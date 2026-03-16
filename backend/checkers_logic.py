import copy

# Board Representation
# 0: empty
# 1: player 1 (Red)
# 2: player 2 (White/Black)
# 3: player 1 King
# 4: player 2 King

EMPTY = 0
P1 = 1
P2 = 2
P1_KING = 3
P2_KING = 4

class CheckersEnvironment:
    def __init__(self):
        self.board = self._init_board()
        self.current_player = P1
        self.winner = None

    def _init_board(self):
        board = [[EMPTY for _ in range(8)] for _ in range(8)]
        for row in range(3):
            for col in range(8):
                if (row + col) % 2 == 1:
                    board[row][col] = P2
        
        for row in range(5, 8):
            for col in range(8):
                if (row + col) % 2 == 1:
                    board[row][col] = P1
        return board

    def get_state(self):
        return {
            "board": copy.deepcopy(self.board),
            "current_player": self.current_player,
            "winner": self.winner
        }

    def set_state(self, state):
        self.board = copy.deepcopy(state["board"])
        self.current_player = state["current_player"]
        self.winner = state.get("winner")

    def is_king(self, piece):
        return piece in (P1_KING, P2_KING)

    def is_opponent(self, player, piece):
        if piece == EMPTY: return False
        if player == P1:
            return piece in (P2, P2_KING)
        else:
            return piece in (P1, P1_KING)

    def is_own(self, player, piece):
        if piece == EMPTY: return False
        if player == P1:
            return piece in (P1, P1_KING)
        else:
            return piece in (P2, P2_KING)

    def get_valid_moves(self, player=None):
        if player is None:
            player = self.current_player
        
        moves = []
        jumps = []
        
        for r in range(8):
            for c in range(8):
                piece = self.board[r][c]
                if self.is_own(player, piece):
                    piece_jumps = self._get_jumps_for_piece(r, c, player, piece)
                    if piece_jumps:
                        jumps.extend(piece_jumps)
                    elif not jumps: # Only look for regular moves if no jumps found yet
                        piece_moves = self._get_moves_for_piece(r, c, player, piece)
                        moves.extend(piece_moves)
                        
        # Checkers requires taking a jump if one is available
        if jumps:
            return jumps
        return moves

    def _get_directions(self, piece):
        if self.is_king(piece):
            return [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        elif piece == P1: # P1 moves "up" (decreasing row index)
            return [(-1, -1), (-1, 1)]
        elif piece == P2: # P2 moves "down" (increasing row index)
            return [(1, -1), (1, 1)]
        return []

    def _get_moves_for_piece(self, r, c, player, piece):
        moves = []
        directions = self._get_directions(piece)
        for dr, dc in directions:
            nr, nc = r + dr, c + dc
            if 0 <= nr < 8 and 0 <= nc < 8 and self.board[nr][nc] == EMPTY:
                moves.append({"start": (r, c), "end": (nr, nc), "jumps": []})
        return moves

    def _get_jumps_for_piece(self, r, c, player, piece, current_path=None, current_jumps=None, board_state=None):
        if current_path is None:
            current_path = [(r, c)]
        if current_jumps is None:
            current_jumps = []
        if board_state is None:
            board_state = [row[:] for row in self.board]

        jumps_found = []
        directions = self._get_directions(piece)

        for dr, dc in directions:
            nr, nc = r + dr, c + dc
            jr, jc = r + 2 * dr, c + 2 * dc # jump destination
            
            if 0 <= jr < 8 and 0 <= jc < 8:
                mid_piece = board_state[nr][nc]
                if self.is_opponent(player, mid_piece) and board_state[jr][jc] == EMPTY:
                    # Valid jump
                    new_board = [row[:] for row in board_state]
                    new_board[r][c] = EMPTY
                    new_board[nr][nc] = EMPTY
                    new_board[jr][jc] = piece # Temporarily move piece

                    new_path = current_path + [(jr, jc)]
                    new_jumped = current_jumps + [(nr, nc)]
                    
                    # Temporarily check king promotion for directionality in multi-jumps
                    temp_piece = piece
                    promoted = False
                    if piece == P1 and jr == 0:
                        temp_piece = P1_KING
                        new_board[jr][jc] = temp_piece
                        promoted = True
                    elif piece == P2 and jr == 7:
                        temp_piece = P2_KING
                        new_board[jr][jc] = temp_piece
                        promoted = True
                        
                    # If promoted, checkers rules usually say turn ends, but we'll stop multi-jump here if promoted
                    further_jumps = []
                    if not promoted:
                        further_jumps = self._get_jumps_for_piece(jr, jc, player, temp_piece, new_path, new_jumped, new_board)
                    
                    if further_jumps:
                        jumps_found.extend(further_jumps)
                    else:
                        jumps_found.append({"start": new_path[0], "end": (jr, jc), "path": new_path, "jumps": new_jumped})
                        
        return jumps_found

    def make_move(self, move):
        if self.winner is not None:
            return False

        r1, c1 = move["start"]
        r2, c2 = move["end"]
        piece = self.board[r1][c1]
        
        # Apply move
        self.board[r1][c1] = EMPTY
        self.board[r2][c2] = piece
        
        # Apply jumps
        for jr, jc in move.get("jumps", []):
            self.board[jr][jc] = EMPTY
            
        # King Promotion
        if piece == P1 and r2 == 0:
            self.board[r2][c2] = P1_KING
        elif piece == P2 and r2 == 7:
            self.board[r2][c2] = P2_KING
            
        # Check Win Condition
        self.current_player = P2 if self.current_player == P1 else P1
        if not self.get_valid_moves():
            self.winner = P2 if self.current_player == P1 else P1
            
        return True

    def print_board(self):
        symbols = {EMPTY: ".", P1: "r", P2: "w", P1_KING: "R", P2_KING: "W"}
        print("  0 1 2 3 4 5 6 7")
        for r in range(8):
            row_str = f"{r} "
            for c in range(8):
                row_str += symbols[self.board[r][c]] + " "
            print(row_str)
        print()
