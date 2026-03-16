import pytest
from backend.checkers_logic import CheckersEnvironment, P1, P2, P1_KING, EMPTY

def test_initial_board():
    env = CheckersEnvironment()
    state = env.get_state()
    assert state["current_player"] == P1
    assert state["winner"] is None
    # Check 12 pieces per player
    board = state["board"]
    p1_count = sum(row.count(P1) for row in board)
    p2_count = sum(row.count(P2) for row in board)
    assert p1_count == 12
    assert p2_count == 12

def test_simple_move():
    env = CheckersEnvironment()
    # P1 moves from 5,0 to 4,1
    move = {"start": (5, 0), "end": (4, 1), "jumps": []}
    success = env.make_move(move)
    assert success
    assert env.get_state()["board"][5][0] == EMPTY
    assert env.get_state()["board"][4][1] == P1
    assert env.get_state()["current_player"] == P2

def test_valid_moves_generation():
    env = CheckersEnvironment()
    moves = env.get_valid_moves()
    # Initial P1 moves should be 7
    assert len(moves) == 7

def test_king_promotion():
    env = CheckersEnvironment()
    board = [[EMPTY for _ in range(8)] for _ in range(8)]
    board[1][1] = P1 # One step from promotion
    env.set_state({"board": board, "current_player": P1, "winner": None})
    
    move = {"start": (1, 1), "end": (0, 0), "jumps": []}
    env.make_move(move)
    
    assert env.get_state()["board"][0][0] == P1_KING
