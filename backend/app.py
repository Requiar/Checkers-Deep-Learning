from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from backend.checkers_logic import CheckersEnvironment, P1, P2
from backend.model import CheckersNet
from backend.mcts import MCTS
import torch

app = FastAPI(title="Checkers Deep Learning AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load dummy model
model = CheckersNet()
try:
    model.load_state_dict(torch.load("backend/model.pt", weights_only=True))
except FileNotFoundError:
    print("WARNING: model.pt not found. Using randomly initialized weights.")
model.eval()

# We only run a small number of simulations for fast API response. 
# In production, this would be much higher, or run asynchronously.
mcts_agent = MCTS(model, num_simulations=50)

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

@app.get("/api/health")
def health_check():
    return {"status": "ok"}

@app.post("/api/start", response_model=GameState)
def start_game():
    env = CheckersEnvironment()
    return env.get_state()

@app.post("/api/move")
def make_move(req: MoveRequest):
    env = CheckersEnvironment()
    state_dict = req.state.dict()
    env.set_state(state_dict)
    
    # We need to convert list coordinates back to tuples
    formatted_move = {
        "start": tuple(req.move["start"]),
        "end": tuple(req.move["end"]),
        "jumps": [tuple(j) for j in req.move.get("jumps", [])]
    }
    
    success = env.make_move(formatted_move)
    if not success:
        raise HTTPException(status_code=400, detail="Invalid move or game over")
        
    return env.get_state()

@app.post("/api/bot-move")
def get_bot_move(req: BotMoveRequest):
    state_dict = req.state.dict()
    
    if state_dict["winner"] is not None:
         raise HTTPException(status_code=400, detail="Game is already over")
         
    # Check if there are any valid moves at all
    env = CheckersEnvironment()
    env.set_state(state_dict)
    if not env.get_valid_moves():
         raise HTTPException(status_code=400, detail="No valid moves available")

    # The MCTS expects a dict
    move, pi = mcts_agent.get_action_prob(state_dict, temperature=req.temperature)
    
    if move is None:
         raise HTTPException(status_code=500, detail="Bot failed to generate a move")
    
    # Apply the move to get the new state
    env.make_move(move)
    
    # Format the move for JSON response (tuples -> lists)
    formatted_reply_move = {
        "start": list(move["start"]),
        "end": list(move["end"]),
        "jumps": [list(j) for j in move.get("jumps", [])]
    }
    
    return {
        "move": formatted_reply_move,
        "new_state": env.get_state()
    }
