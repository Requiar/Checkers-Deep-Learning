const API_URL = 'http://localhost:8000/api';

let gameState = null;
let selectedPiece = null;
let validMoveDestinations = {};

// Board Representation Map
const EMPTY = 0;
const P1 = 1;      // Human
const P2 = 2;      // Bot
const P1_KING = 3;
const P2_KING = 4;

const boardElement = document.getElementById('checkers-board');
const statusText = document.getElementById('game-status-text');
const btnStart = document.getElementById('btn-start');
const tempSlider = document.getElementById('temperature-slider');
const tempValue = document.getElementById('temp-value');
const loadingOverlay = document.getElementById('loading-overlay');

// UI Init
tempSlider.addEventListener('input', (e) => {
    tempValue.textContent = e.target.value;
});

btnStart.addEventListener('click', startGame);

async function startGame() {
    try {
        const response = await fetch(`${API_URL}/start`, { method: 'POST' });
        gameState = await response.json();
        renderBoard();
        updateStatus();
    } catch (err) {
        console.error("Failed to start game:", err);
        statusText.textContent = "Server Error";
    }
}

function renderBoard() {
    boardElement.innerHTML = '';
    validMoveDestinations = {};
    
    // We only need to compute valid destinations if a piece is selected
    if (selectedPiece && gameState.current_player === P1) {
        // Since we don't have a get_valid_moves API endpoint right now, 
        // the simplest frontend implementation is to let the user click anywhere
        // and let the backend reject invalid moves. 
        // For a better UX, we'd add an endpoint or duplicate move logic in JS.
        // For this demo, we'll implement optimistic clicking.
    }

    for (let r = 0; r < 8; r++) {
        for (let c = 0; c < 8; c++) {
            const cell = document.createElement('div');
            cell.dataset.r = r;
            cell.dataset.c = c;
            
            // Checkerboard pattern
            if ((r + c) % 2 === 0) {
                cell.classList.add('cell', 'light');
            } else {
                cell.classList.add('cell', 'dark');
                // Only dark squares can contain pieces and be clicked
                cell.addEventListener('click', () => handleCellClick(r, c));
            }

            const pieceVal = gameState.board[r][c];
            if (pieceVal !== EMPTY) {
                const piece = document.createElement('div');
                piece.classList.add('piece');
                piece.classList.add('anim-enter');
                
                if (pieceVal === P1 || pieceVal === P1_KING) piece.classList.add('p1');
                if (pieceVal === P2 || pieceVal === P2_KING) piece.classList.add('p2');
                if (pieceVal === P1_KING || pieceVal === P2_KING) piece.classList.add('king');

                if (selectedPiece && selectedPiece.r === r && selectedPiece.c === c) {
                    piece.classList.add('selected');
                }

                cell.appendChild(piece);
            }

            boardElement.appendChild(cell);
        }
    }
}

async function handleCellClick(r, c) {
    if (!gameState || gameState.winner !== null || gameState.current_player !== P1) return;

    const pieceVal = gameState.board[r][c];
    
    // Selecting own piece
    if (pieceVal === P1 || pieceVal === P1_KING) {
        selectedPiece = { r, c };
        renderBoard();
        return;
    }

    // Moving selected piece to empty dark square
    if (selectedPiece && pieceVal === EMPTY) {
        // We try to make the move. The backend validates it.
        // For a real game, you would pass the full jump path if it was a multi-jump.
        // To keep this simple we just pass start and end, and let backend figure out jumps
        // (Our backend currently expects explicit jumps, but we will simplify the FE by just
        // trying single leaps. If a user tries a jump, we attempt to deduce the jumped piece).
        
        await attemptMove(selectedPiece.r, selectedPiece.c, r, c);
    }
}

async function attemptMove(startR, startC, endR, endC) {
    // Quick heuristic to find jumped piece for simple 1-step jumps
    let jumps = [];
    if (Math.abs(startR - endR) === 2) {
        jumps.push([(startR + endR)/2, (startC + endC)/2]);
    }
    
    const movePayload = {
        state: gameState,
        move: { start: [startR, startC], end: [endR, endC], jumps: jumps }
    };

    try {
        const response = await fetch(`${API_URL}/move`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(movePayload)
        });

        if (!response.ok) {
            console.warn("Invalid move");
            selectedPiece = null;
            renderBoard();
            return;
        }

        gameState = await response.json();
        selectedPiece = null;
        renderBoard();
        updateStatus();

        if (gameState.winner === null && gameState.current_player === P2) {
            requestBotMove();
        }
    } catch (err) {
        console.error("Move request failed", err);
    }
}

async function requestBotMove() {
    loadingOverlay.classList.remove('hidden');
    statusText.textContent = "Bot is thinking...";
    
    const temperature = parseFloat(tempSlider.value);
    
    try {
        const response = await fetch(`${API_URL}/bot-move`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ state: gameState, temperature: temperature })
        });

        if (!response.ok) throw new Error("Bot move failed");

        const data = await response.json();
        gameState = data.new_state;
        
        // Minor delay for better UX
        setTimeout(() => {
            loadingOverlay.classList.add('hidden');
            renderBoard();
            updateStatus();
        }, 500);

    } catch (err) {
        console.error("Bot AI error", err);
        loadingOverlay.classList.add('hidden');
        statusText.textContent = "Bot Error";
    }
}

function updateStatus() {
    if (gameState.winner === P1) {
        statusText.textContent = "You Win! 🎉";
        statusText.style.color = "#00f2fe";
    } else if (gameState.winner === P2) {
        statusText.textContent = "Bot Wins! 🤖";
        statusText.style.color = "#ff3366";
    } else {
        statusText.textContent = gameState.current_player === P1 ? "Your Turn (Red)" : "Bot's Turn (White)";
        statusText.style.color = "var(--text-secondary)";
    }
}
