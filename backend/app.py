from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from backend.checkers_logic import CheckersEnvironment, P1, P2
from backend.model import CheckersNet
from backend.mcts import MCTS, encode_board
from backend.ranking import EloRanking
import torch
import json
import os

app = FastAPI(title="Checkers Deep Learning AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load all models from catalog
models_db = {}
mcts_agents = {}
bot_metadata = {}

try:
    with open("backend/models/catalog.json", "r") as f:
        bot_metadata = json.load(f)
        
    for bot_id, data in bot_metadata.items():
        if bot_id == "bot_random":
            mcts_agents[bot_id] = "RANDOM"
            continue
            
        cfg = data["config"]
        # Instantiate model with its specific shape
        m = CheckersNet(
            num_res_blocks=cfg["layers"],
            channels=cfg["channels"],
            dropout_rate=0.0 # eval mode
        )
        try:
            m.load_state_dict(torch.load(data["weight_path"], weights_only=True))
            m.eval()
            models_db[bot_id] = m
            # We initialize MCTS, but num_simulations can be overridden per request
            mcts_agents[bot_id] = MCTS(m, num_simulations=50)
        except Exception as e:
            print(f"Failed to load weights for {bot_id}: {e}")
            
except FileNotFoundError:
    print("WARNING: catalog.json not found. Run train.py first to generate the multi-bot catalog.")
    
# Load Elo Ratings
elo_ratings = {}
try:
    with open("backend/elo_ratings.json", "r") as f:
        elo_ratings = json.load(f)
except FileNotFoundError:
    print("WARNING: elo_ratings.json not found.")

class GameState(BaseModel):
    board: List[List[int]]
    current_player: int
    winner: Optional[int] = None

class MoveRequest(BaseModel):
    state: GameState
    move: Dict[str, Any] # {"start": [r, c], "end": [r, c], "jumps": [...]}

class BotMoveRequest(BaseModel):
    state: GameState
    temperature: float = 0.5
    bot_id: str = "bot_v1_baseline"
    search_depth: int = 50

class WinProbRequest(BaseModel):
    state: GameState
    bot_id: str = "bot_v1_baseline"

class TournamentRequest(BaseModel):
    bot1_id: str # Plays Red (P1)
    bot2_id: str # Plays White (P2)
    num_games: int = 5
    search_depth: int = 20
    temperature: float = 0.5
    max_moves: int = 150 # Prevent infinite loops

@app.get("/api/health")
def health_check():
    return {"status": "ok"}

@app.get("/api/bots")
def get_bots():
    """Returns the list of available bots, configs, losses, and real-time Elo ratings."""
    bots_payload = []
    for bot_id, meta in bot_metadata.items():
        bot_info = dict(meta)
        bot_info["id"] = bot_id
        bot_info["elo"] = elo_ratings.get(bot_id, 1000)
        bots_payload.append(bot_info)
    return {"bots": bots_payload}

@app.post("/api/start", response_model=GameState)
def start_game():
    env = CheckersEnvironment()
    return env.get_state()

@app.post("/api/valid-moves")
def get_valid_moves(req: GameState):
    env = CheckersEnvironment()
    env.set_state(req.dict())
    moves = env.get_valid_moves()
    
    # Format moves for JSON 
    formatted_moves = []
    for m in moves:
        formatted_moves.append({
            "start": list(m["start"]),
            "end": list(m["end"]),
            "jumps": [list(j) for j in m.get("jumps", [])]
        })
    return {"moves": formatted_moves}

@app.post("/api/move")
def make_move(req: MoveRequest):
    env = CheckersEnvironment()
    state_dict = req.state.dict()
    env.set_state(state_dict)
    
    formatted_move = {
        "start": tuple(req.move["start"]),
        "end": tuple(req.move["end"]),
        "jumps": [tuple(j) for j in req.move.get("jumps", [])]
    }
    
    # Strictly validate against engine's legal moves
    valid_moves = env.get_valid_moves()
    is_legal = False
    for vm in valid_moves:
        if vm["start"] == formatted_move["start"] and vm["end"] == formatted_move["end"]:
            # Also require jumps to match to prevent skipping multi-jumps
            if set(vm.get("jumps", [])) == set(formatted_move.get("jumps", [])):
                is_legal = True
                break
                
    if not is_legal:
         raise HTTPException(status_code=400, detail="Move is strictly illegal")
    
    success = env.make_move(formatted_move)
    if not success:
        raise HTTPException(status_code=400, detail="State error applying move")
        
    return env.get_state()

@app.post("/api/bot-move")
def get_bot_move(req: BotMoveRequest):
    state_dict = req.state.dict()
    
    if state_dict["winner"] is not None:
         raise HTTPException(status_code=400, detail="Game is already over")
         
    env = CheckersEnvironment()
    env.set_state(state_dict)
    valid_moves = env.get_valid_moves()
    if not valid_moves:
         raise HTTPException(status_code=400, detail="No valid moves available")
         
    bot_id = req.bot_id
    if bot_id not in mcts_agents:
         raise HTTPException(status_code=404, detail="Bot ID not found")
         
    agent = mcts_agents[bot_id]
    
    if agent == "RANDOM":
        import random
        move = random.choice(valid_moves)
    else:
        # Dynamically set simulations depth for this request
        agent.num_simulations = req.search_depth
        move, pi = agent.get_action_prob(state_dict, temperature=req.temperature)
        
    if move is None:
         raise HTTPException(status_code=500, detail="Bot failed to generate a move")
    
    env.make_move(move)
    
    formatted_reply_move = {
        "start": list(move["start"]),
        "end": list(move["end"]),
        "jumps": [list(j) for j in move.get("jumps", [])]
    }
    
    return {
        "move": formatted_reply_move,
        "new_state": env.get_state()
    }

@app.post("/api/win-probability")
def get_win_probability(req: WinProbRequest):
    """
    Evaluates the board using the requested bot's Value Head.
    Returns a probability between 0 and 1 of current_player winning.
    """
    bot_id = req.bot_id
    if bot_id == "bot_random" or bot_id not in models_db:
        return {"win_probability": 0.5} # Neutral fallback
        
    model = models_db[bot_id]
    state_dict = req.state.dict()
    
    board_tensor = encode_board(state_dict)
    with torch.no_grad():
        _, value_tensor = model(board_tensor)
        
    value = value_tensor.item() # Maps roughly to [-1, 1]
    
    # Map hyperbolic tangent output [-1, 1] linearly to a probability [0.0, 1.0] representing 
    # the advantage for the current player whose turn it is
    win_prob = (value + 1.0) / 2.0 
    
    return {"win_probability": win_prob}

@app.post("/api/tournament")
def run_tournament(req: TournamentRequest):
    if req.bot1_id not in mcts_agents or req.bot2_id not in mcts_agents:
        raise HTTPException(status_code=404, detail="One or more Bot IDs not found")
        
    wins_1 = 0
    wins_2 = 0
    draws = 0
    
    agent1 = mcts_agents[req.bot1_id]
    agent2 = mcts_agents[req.bot2_id]
    
    for game_idx in range(req.num_games):
        env = CheckersEnvironment()
        move_count = 0
        
        while env.winner is None and move_count < req.max_moves:
            valid_moves = env.get_valid_moves()
            if not valid_moves:
                break # game over (no moves left)
                
            current_agent = agent1 if env.current_player == P1 else agent2
            
            if current_agent == "RANDOM":
                import random
                move = random.choice(valid_moves)
            else:
                current_agent.num_simulations = req.search_depth
                move, _ = current_agent.get_action_prob(env.get_state(), temperature=req.temperature)
                if move is None:
                    break
                    
            env.make_move(move)
            move_count += 1
            
        # Tally results
        if env.winner == P1:
            wins_1 += 1
        elif env.winner == P2:
            wins_2 += 1
        else:
            draws += 1 # Includes games that hit max_moves (stalemates)
            
    # Update global Elo ratings based on tournament games
    ranking = EloRanking(alpha=0.01)
    ranking.ratings = elo_ratings # load live dictionary
    
    # Process each match sequentially
    for _ in range(wins_1):
        ranking.update_ratings(req.bot1_id, req.bot2_id, outcome_i=1.0)
    for _ in range(wins_2):
        ranking.update_ratings(req.bot1_id, req.bot2_id, outcome_i=0.0)
    for _ in range(draws):
        ranking.update_ratings(req.bot1_id, req.bot2_id, outcome_i=0.5)
        
    ranking.save("backend/elo_ratings.json")
    
    return {
        "bot1": req.bot1_id,
        "bot2": req.bot2_id,
        "wins_1": wins_1,
        "wins_2": wins_2,
        "draws": draws,
        "new_elo_1": ranking.get_rating(req.bot1_id),
        "new_elo_2": ranking.get_rating(req.bot2_id)
    }
