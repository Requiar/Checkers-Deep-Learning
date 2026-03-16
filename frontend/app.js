const API_URL = 'http://localhost:8000/api';

let gameState = null;
let selectedPiece = null;
let validMoves = []; // List of all valid move objects for the current turn
let validDestinationsMap = {}; // Maps `${startR},${startC}` to a list of allowed end coordinates

// History
let stateHistory = [];
let currentHistoryIndex = -1;

// Player Color Preference
let playerIsRed = true;

// Board Representation Map
const EMPTY = 0;
const P1 = 1;      // Human
const P2 = 2;      // Bot
const P1_KING = 3;
const P2_KING = 4;

const boardElement = document.getElementById('checkers-board');
const statusText = document.getElementById('game-status-text');
const btnStart = document.getElementById('btn-start');
const colorToggle = document.getElementById('color-toggle');
const legendP1Text = document.getElementById('legend-p1-text');
const legendP2Text = document.getElementById('legend-p2-text');
const tempSlider = document.getElementById('temperature-slider');
const tempValue = document.getElementById('temp-value');
const loadingOverlay = document.getElementById('loading-overlay');
const btnPrev = document.getElementById('btn-prev');
const btnNext = document.getElementById('btn-next');
const btnCurrent = document.getElementById('btn-current');

function updateHistoryControls() {
    if (btnPrev && btnNext && btnCurrent) {
        btnPrev.disabled = currentHistoryIndex <= 0;
        btnNext.disabled = currentHistoryIndex >= stateHistory.length - 1;
        btnCurrent.disabled = currentHistoryIndex === stateHistory.length - 1;
    }
}

if (btnPrev) {
    btnPrev.addEventListener('click', () => {
        if (currentHistoryIndex > 0) {
            currentHistoryIndex--;
            gameState = JSON.parse(JSON.stringify(stateHistory[currentHistoryIndex]));
            updateHistoryControls();
            renderBoard();
            updateStatus();
        }
    });
}

if (btnNext) {
    btnNext.addEventListener('click', () => {
        if (currentHistoryIndex < stateHistory.length - 1) {
            currentHistoryIndex++;
            gameState = JSON.parse(JSON.stringify(stateHistory[currentHistoryIndex]));
            updateHistoryControls();
            renderBoard();
            updateStatus();
        }
    });
}

if (btnCurrent) {
    btnCurrent.addEventListener('click', () => {
        currentHistoryIndex = stateHistory.length - 1;
        gameState = JSON.parse(JSON.stringify(stateHistory[currentHistoryIndex]));
        updateHistoryControls();
        renderBoard();
        updateStatus();
    });
}

// UI Init
colorToggle.addEventListener('click', (e) => {
    e.preventDefault();
    playerIsRed = !playerIsRed;
    colorToggle.textContent = playerIsRed ? "Play as White instead" : "Play as Red instead";
    legendP1Text.textContent = playerIsRed ? "You (Red)" : "Bot (Red)";
    legendP2Text.textContent = playerIsRed ? "Bot (White)" : "You (White)";
});

tempSlider.addEventListener('input', (e) => {
    tempValue.textContent = e.target.value;
});

btnStart.addEventListener('click', startGame);

async function startGame() {
    try {
        const response = await fetch(`${API_URL}/start`, { method: 'POST' });
        gameState = await response.json();
        
        stateHistory = [JSON.parse(JSON.stringify(gameState))];
        currentHistoryIndex = 0;
        updateHistoryControls();
        
        // If player chose white, let AI move first
        if (!playerIsRed) {
            await fetchValidMoves(); // Even if it's the bot's turn, we can fetch
            requestBotMove();
        } else {
            await fetchValidMoves();
            renderBoard();
            updateStatus();
        }
    } catch (err) {
        console.error("Failed to start game:", err);
        statusText.textContent = "Server Error";
    }
}

async function fetchValidMoves() {
    if (!gameState || gameState.winner !== null) return;
    try {
        const response = await fetch(`${API_URL}/valid-moves`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(gameState)
        });
        const data = await response.json();
        validMoves = data.moves;
        
        validDestinationsMap = {};
        for (const m of validMoves) {
            const startKey = `${m.start[0]},${m.start[1]}`;
            if (!validDestinationsMap[startKey]) {
                validDestinationsMap[startKey] = [];
            }
            validDestinationsMap[startKey].push(m);
        }
    } catch (err) {
        console.error("Failed to fetch valid moves:", err);
    }
}

function renderBoard() {
    boardElement.innerHTML = '';
    
    // Determine the mapped perspective
    const playerPerspective = playerIsRed ? P1 : P2;
    const botPerspective = playerIsRed ? P2 : P1;

    let allowedDestinations = [];
    if (selectedPiece) {
        const startKey = `${selectedPiece.r},${selectedPiece.c}`;
        if (validDestinationsMap[startKey]) {
            allowedDestinations = validDestinationsMap[startKey].map(m => `${m.end[0]},${m.end[1]}`);
        }
    }

    for (let visualR = 0; visualR < 8; visualR++) {
        for (let visualC = 0; visualC < 8; visualC++) {
            const r = playerIsRed ? visualR : 7 - visualR;
            const c = playerIsRed ? visualC : 7 - visualC;
            
            const cell = document.createElement('div');
            cell.dataset.r = r;
            cell.dataset.c = c;
            
            // Checkerboard pattern
            if ((r + c) % 2 === 0) {
                cell.classList.add('cell', 'light');
            } else {
                cell.classList.add('cell', 'dark');
                
                // Highlight if it's a valid destination for the selected piece
                if (allowedDestinations.includes(`${r},${c}`)) {
                     cell.classList.add('highlight');
                }
                
                // Only dark squares can contain pieces and be clicked
                cell.addEventListener('click', () => handleCellClick(r, c));
            }

            const pieceVal = gameState.board[r][c];
            if (pieceVal !== EMPTY) {
                const piece = document.createElement('div');
                piece.classList.add('piece');
                piece.classList.add('anim-enter');
                
                // Color mapping: P1 is always visually at the bottom, P2 at the top.
                // Wait, if playerIsRed=false, they are P2. 
                // But the backend `checkers_logic` handles moves strictly with P1 going "up" (decreasing row)
                // and P2 going "down" (increasing row). 
                // To keep this simple visually, we just map the colors.
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
    if (!gameState || gameState.winner !== null) return;
    
    // Disable moves while in history review mode
    if (currentHistoryIndex !== stateHistory.length - 1) return;
    
    const pID = playerIsRed ? P1 : P2;
    if (gameState.current_player !== pID) return;

    const pieceVal = gameState.board[r][c];
    
    // Selecting own piece
    if ((pID === P1 && (pieceVal === P1 || pieceVal === P1_KING)) || 
        (pID === P2 && (pieceVal === P2 || pieceVal === P2_KING))) {
            
        selectedPiece = { r, c };
        renderBoard();
        return;
    }

    // Moving selected piece to empty dark square
    if (selectedPiece && pieceVal === EMPTY) {
        // Find the exact valid move
        const startKey = `${selectedPiece.r},${selectedPiece.c}`;
        const possibleMoves = validDestinationsMap[startKey] || [];
        
        const matchedMove = possibleMoves.find(m => m.end[0] === r && m.end[1] === c);
        
        if (matchedMove) {
             await attemptMove(matchedMove);
        } else {
             // Clicked an invalid empty square; deselect
             selectedPiece = null;
             renderBoard();
        }
    }
}

async function attemptMove(moveObj) {
    const movePayload = {
        state: gameState,
        move: moveObj
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
        stateHistory.push(JSON.parse(JSON.stringify(gameState)));
        currentHistoryIndex = stateHistory.length - 1;
        updateHistoryControls();
        
        selectedPiece = null;
        await fetchValidMoves();
        renderBoard();
        updateStatus();

        const pID = playerIsRed ? P1 : P2;
        const botID = playerIsRed ? P2 : P1;

        if (gameState.winner === null && gameState.current_player === botID) {
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
        
        stateHistory.push(JSON.parse(JSON.stringify(gameState)));
        currentHistoryIndex = stateHistory.length - 1;
        updateHistoryControls();
        
        // Minor delay for better UX
        setTimeout(async () => {
            loadingOverlay.classList.add('hidden');
            await fetchValidMoves();
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
    const pID = playerIsRed ? P1 : P2;
    
    // Modify text string if playing in the past
    let prefix = currentHistoryIndex !== stateHistory.length - 1 ? "[REVIEW] " : "";
    
    if (gameState.winner === pID) {
        statusText.textContent = prefix + "You Win! 🎉";
        statusText.style.color = "#00f2fe";
    } else if (gameState.winner !== null && gameState.winner !== pID) {
        statusText.textContent = prefix + "Bot Wins! 🤖";
        statusText.style.color = "#ff3366";
    } else {
        const turnText = gameState.current_player === pID ? "Your Turn" : "Bot's Turn";
        statusText.textContent = prefix + turnText;
        statusText.style.color = "var(--text-secondary)";
    }
}
