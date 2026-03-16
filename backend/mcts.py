import math
import numpy as np
import torch
import copy
from backend.checkers_logic import CheckersEnvironment, P1, P2

class MCTSNode:
    def __init__(self, state, player, parent=None, move=None):
        self.state = state  # The board state dict
        self.player = player
        self.parent = parent
        self.move = move
        self.children = {}  # action_idx: MCTSNode
        
        self.visits = 0
        self.value_sum = 0
        self.prior = 0.0

    def get_value(self):
        if self.visits == 0:
            return 0
        return self.value_sum / self.visits

def encode_board(state):
    # state is a dict with 'board' (8x8 list)
    board = np.array(state["board"])
    
    # 5 channels: empty, P1, P2, P1_King, P2_King
    encoded = np.zeros((5, 8, 8), dtype=np.float32)
    encoded[0] = (board == 0).astype(np.float32)
    encoded[1] = (board == 1).astype(np.float32)
    encoded[2] = (board == 2).astype(np.float32)
    encoded[3] = (board == 3).astype(np.float32)
    encoded[4] = (board == 4).astype(np.float32)
    
    return torch.tensor(encoded).unsqueeze(0)  # Add batch dimension

def get_action_index(move):
    # A simple but flawed hash for demonstration.
    # In a real engine, we'd map standard checkers notation or 
    # specific from-to coordinate pairs to a 1D vector index (0-127).
    r1, c1 = move["start"]
    r2, c2 = move["end"]
    return (r1 * 8 + c1) * 64 + (r2 * 8 + c2) % 128

class MCTS:
    def __init__(self, model, num_simulations=100, c_puct=1.0):
        self.model = model
        self.num_simulations = num_simulations
        self.c_puct = c_puct

    def search(self, initial_state):
        env = CheckersEnvironment()
        env.set_state(initial_state)
        
        root = MCTSNode(state=env.get_state(), player=env.current_player)

        for _ in range(self.num_simulations):
            node = root
            search_env = CheckersEnvironment()
            search_env.set_state(node.state)

            # 1. Select
            while len(node.children) > 0:
                # UCB selection
                best_u = -float('inf')
                best_action = None
                best_node = None
                
                for action, child in node.children.items():
                    u = child.get_value() + self.c_puct * child.prior * math.sqrt(node.visits + 1e-8) / (1 + child.visits)
                    if u > best_u:
                        best_u = u
                        best_action = action
                        best_node = child
                        
                node = best_node
                search_env.make_move(node.move)

            # 2. Expand & Evaluate
            valid_moves = search_env.get_valid_moves(search_env.current_player)
            
            if search_env.winner is not None or not valid_moves:
                # Terminal state
                if search_env.winner == initial_state["current_player"]:
                    value = 1.0
                elif search_env.winner is None:
                    value = 0.0
                else:
                    value = -1.0
            else:
                # Neural Net Evaluation
                board_tensor = encode_board(search_env.get_state())
                with torch.no_grad():
                    policy_logits, value_tensor = self.model(board_tensor)
                
                value = value_tensor.item()
                policy = torch.softmax(policy_logits[0], dim=0).cpu().numpy()
                
                # Expand
                for move in valid_moves:
                    act_idx = get_action_index(move) % 128 # Keep within bounds for simplicity
                    
                    child_state = copy.deepcopy(search_env.get_state())
                    temp_env = CheckersEnvironment()
                    temp_env.set_state(child_state)
                    temp_env.make_move(move)
                    
                    child = MCTSNode(state=temp_env.get_state(), 
                                     player=temp_env.current_player,
                                     parent=node,
                                     move=move)
                    child.prior = float(policy[act_idx])
                    node.children[act_idx] = child

            # 3. Backpropagate
            while node is not None:
                node.visits += 1
                node.value_sum += value
                node = node.parent
                value = -value # switch perspective for parent

        return root

    def get_action_prob(self, state, temperature=1.0):
        # Edge case: temperature 0 means pure greedy
        root = self.search(state)
        
        action_visits = {}
        for act_idx, child in root.children.items():
            action_visits[act_idx] = child.visits
            
        if not action_visits:
            # Fallback if no valid moves (shouldn't be called if game over)
            return None, {}
            
        actions = list(action_visits.keys())
        visits = list(action_visits.values())
        
        if temperature < 1e-3: # essentially deterministic (greedy)
            best_action = actions[np.argmax(visits)]
            probs = np.zeros(len(actions))
            probs[np.argmax(visits)] = 1.0
        else: # Softmax based on temperature
            visits = np.array(visits, dtype=np.float64)
            visits = visits ** (1.0 / temperature)
            # Avoid overflow/division by zero
            sum_visits = np.sum(visits)
            if sum_visits == 0:
                probs = np.ones(len(actions)) / len(actions)
            else:
                probs = visits / sum_visits
                
            best_action = np.random.choice(actions, p=probs)
            
        # Return the actual move dict corresponding to the chosen action
        chosen_move = root.children[best_action].move
        
        # Build full prob vector (mostly for training/debugging)
        pi = np.zeros(128)
        for act, prob in zip(actions, probs):
             pi[act] = prob
             
        return chosen_move, pi
