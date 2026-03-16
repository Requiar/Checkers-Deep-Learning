"""
Minimax with Alpha-Beta Pruning for Checkers
=============================================
Used for fast self-play data generation. Does NOT use the neural network.
Instead uses a simple heuristic (piece counting + positional bonuses)
to evaluate leaf nodes, making it fast enough to generate hundreds of games.
"""

import math
import random
import numpy as np
from backend.checkers_logic import CheckersEnvironment, P1, P2, P1_KING, P2_KING, EMPTY


def heuristic_eval(env):
    """
    Simple board evaluation heuristic.
    Positive = good for P1 (Red), Negative = good for P2 (White).
    
    - Regular piece = 1.0
    - King = 1.5
    - Center control bonus = 0.3 per piece in center 4 squares
    """
    score = 0.0
    center = {(3, 3), (3, 4), (4, 3), (4, 4)}
    
    for r in range(8):
        for c in range(8):
            piece = env.board[r][c]
            if piece == P1:
                score += 1.0
                if (r, c) in center:
                    score += 0.3
            elif piece == P1_KING:
                score += 1.5
                if (r, c) in center:
                    score += 0.3
            elif piece == P2:
                score -= 1.0
                if (r, c) in center:
                    score -= 0.3
            elif piece == P2_KING:
                score -= 1.5
                if (r, c) in center:
                    score -= 0.3
    return score


def minimax(env, depth, alpha, beta, maximizing):
    """
    Minimax with alpha-beta pruning.
    
    Args:
        env: CheckersEnvironment instance
        depth: remaining search depth
        alpha: alpha bound
        beta: beta bound
        maximizing: True if current player is P1 (maximizing)
    
    Returns:
        (score, best_move)
    """
    if env.winner is not None:
        if env.winner == P1:
            return 100.0, None
        elif env.winner == P2:
            return -100.0, None
        else:
            return 0.0, None
    
    if depth == 0:
        return heuristic_eval(env), None
    
    valid_moves = env.get_valid_moves()
    if not valid_moves:
        # No moves = loss for current player
        if env.current_player == P1:
            return -100.0, None
        else:
            return 100.0, None
    
    best_move = valid_moves[0]
    
    if maximizing:
        max_eval = -math.inf
        for move in valid_moves:
            child_env = CheckersEnvironment()
            child_env.set_state(env.get_state())
            child_env.make_move(move)
            
            eval_score, _ = minimax(child_env, depth - 1, alpha, beta, False)
            if eval_score > max_eval:
                max_eval = eval_score
                best_move = move
            alpha = max(alpha, eval_score)
            if beta <= alpha:
                break  # Beta cutoff
        return max_eval, best_move
    else:
        min_eval = math.inf
        for move in valid_moves:
            child_env = CheckersEnvironment()
            child_env.set_state(env.get_state())
            child_env.make_move(move)
            
            eval_score, _ = minimax(child_env, depth - 1, alpha, beta, True)
            if eval_score < min_eval:
                min_eval = eval_score
                best_move = move
            beta = min(beta, eval_score)
            if beta <= alpha:
                break  # Alpha cutoff
        return min_eval, best_move


def get_best_move_minimax(env, depth=4, temperature=1.0):
    """
    Select a move using minimax scores + softmax temperature sampling.
    
    At temperature=0, always picks the best move (greedy).
    At higher temperatures, samples proportionally to score quality.
    """
    valid_moves = env.get_valid_moves()
    if not valid_moves:
        return None
    
    if len(valid_moves) == 1:
        return valid_moves[0]
    
    maximizing = (env.current_player == P1)
    scores = []
    
    for move in valid_moves:
        child_env = CheckersEnvironment()
        child_env.set_state(env.get_state())
        child_env.make_move(move)
        
        score, _ = minimax(child_env, depth - 1, -math.inf, math.inf, not maximizing)
        scores.append(score)
    
    scores = np.array(scores, dtype=np.float64)
    
    # Flip scores for P2 (minimizing player wants lowest score)
    if not maximizing:
        scores = -scores
    
    if temperature < 1e-4:
        # Greedy
        return valid_moves[int(np.argmax(scores))]
    
    # Softmax sampling
    scores = scores / temperature
    scores -= np.max(scores)  # Numerical stability
    exp_scores = np.exp(scores)
    probs = exp_scores / np.sum(exp_scores)
    
    idx = np.random.choice(len(valid_moves), p=probs)
    return valid_moves[idx]
