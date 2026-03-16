const API_URL = 'http://localhost:8000/api';

let gameState = null;
let selectedPiece = null;
let validMoves = []; 
let validDestinationsMap = {}; 

let stateHistory = [];
let currentHistoryIndex = -1;

let availableBots = [];
let activeMatch = false;

const boardElement = document.getElementById('checkers-board');
const statusText = document.getElementById('game-status-text');
const btnStart = document.getElementById('btn-start');
const btnTourney = document.getElementById('btn-tourney');
const p1Select = document.getElementById('p1-select');
const p2Select = document.getElementById('p2-select');
const legendP1Text = document.getElementById('legend-p1-text');
const legendP2Text = document.getElementById('legend-p2-text');
const tempSlider = document.getElementById('temperature-slider');
const tempValue = document.getElementById('temp-value');
const depthSlider = document.getElementById('depth-slider');
const depthValue = document.getElementById('depth-value');
const loadingOverlay = document.getElementById('loading-overlay');
const btnPrev = document.getElementById('btn-prev');
const btnNext = document.getElementById('btn-next');
const btnCurrent = document.getElementById('btn-current');
const probBarFill = document.getElementById('prob-bar-fill');
const probText = document.getElementById('prob-text');

// Board Represents
const EMPTY = 0;
const P1 = 1;      // Red
const P2 = 2;      // White
const P1_KING = 3;
const P2_KING = 4;

// Initialization
async function initializeApp() {
    try {
        const response = await fetch(`${API_URL}/bots`);
        const data = await response.json();
        availableBots = data.bots;
        
        let botOptionsHTML = '';
        availableBots.forEach(bot => {
            botOptionsHTML += `<option value="${bot.id}">${bot.name} (Elo: ${Math.round(bot.elo)})</option>`;
        });
        
        p1Select.innerHTML = `<option value="human">Human</option>` + botOptionsHTML;
        p2Select.innerHTML = `<option value="human">Human</option>` + botOptionsHTML;
        
        // Default P2 to the baseline bot if it exists
        if(availableBots.length > 0) p2Select.value = availableBots[0].id;
        
    } catch (err) {
        console.error("Failed to load bots:", err);
    }
}
window.addEventListener('DOMContentLoaded', initializeApp);

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
            selectedPiece = null;
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
            selectedPiece = null;
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
        selectedPiece = null;
        renderBoard();
        updateStatus();
    });
}

tempSlider.addEventListener('input', (e) => tempValue.textContent = e.target.value);
depthSlider.addEventListener('input', (e) => depthValue.textContent = e.target.value);

btnTourney.addEventListener('click', runTournament);
btnStart.addEventListener('click', startGame);

async function updateWinProbability() {
    if (!gameState) return;
    
    // Choose which bot evaluates the board. Default to whoever is P2, else P1.
    let evaluatorId = p2Select.value !== "human" ? p2Select.value : (p1Select.value !== "human" ? p1Select.value : null);
    
    if(!evaluatorId) {
        // If human vs human, we can't really evaluate easily without picking a random bot.
        // Let's just pick the first available bot if it exists
        if (availableBots.length > 0) evaluatorId = availableBots[0].id;
        else return;
    }
    
    try {
        const payload = { state: gameState, bot_id: evaluatorId };
        const response = await fetch(`${API_URL}/win-probability`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        const data = await response.json();
        // The endpoint returns win_probability from the perspective of the CURRENT player.
        // We want to map this purely to Red (P1) vs White (P2).
        let redAdvantage = data.win_probability;
        if (gameState.current_player === P2) {
             redAdvantage = 1.0 - redAdvantage;
        }
        
        const redPct = Math.round(redAdvantage * 100);
        const whitePct = 100 - redPct;
        
        probText.textContent = `${redPct}% / ${whitePct}%`;
        probBarFill.style.width = `${redPct}%`;
        
    } catch (err) {
        console.error("Failed to fetch win probability", err);
    }
}

async function runTournament() {
    activeMatch = false;
    loadingOverlay.classList.remove('hidden');
    
    const numGames = prompt("How many games should EACH PAIR of bots play against each other?", "2");
    if(!numGames) { loadingOverlay.classList.add('hidden'); return; }
    
    document.querySelector('#loading-overlay p').textContent = `Running ${numGames} games per pair in the cloud...`;
    
    try {
        const payload = {
            num_games: parseInt(numGames),
            search_depth: parseInt(depthSlider.value),
            temperature: parseFloat(tempSlider.value)
        };
        
        const response = await fetch(`${API_URL}/tournament`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        const results = await response.json();
        
        let msg = `Tournament Complete! (${results.matches_played} total games)\n\n--- Elo Changes ---\n`;
        for (const [botId, elo] of Object.entries(results.final_elos)) {
             msg += `${botId}: ${elo}\n`;
        }
        
        msg += `\n--- Matchups ---\n`;
        results.matchups.forEach(m => {
             msg += `${m.matchup} -> W1: ${m.bot1_wins}, W2: ${m.bot2_wins}, D: ${m.draws}\n`;
        });
        
        alert(msg);
        
        // Refresh bots array to get new Elos
        await initializeApp(); 
        
    } catch(err) {
        console.error("Tournament Failed", err);
        alert("Tournament Failed. Check console.");
    } finally {
        loadingOverlay.classList.add('hidden');
        document.querySelector('#loading-overlay p').textContent = "Bot is thinking...";
    }
}

async function startGame() {
    try {
        const response = await fetch(`${API_URL}/start`, { method: 'POST' });
        gameState = await response.json();
        
        stateHistory = [JSON.parse(JSON.stringify(gameState))];
        currentHistoryIndex = 0;
        updateHistoryControls();
        activeMatch = true;
        
        p1Select.disabled = true;
        p2Select.disabled = true;
        
        checkAndExecuteTurn();
    } catch (err) {
        console.error("Failed to start game:", err);
        statusText.textContent = "Server Error";
    }
}

async function checkAndExecuteTurn() {
    if (!activeMatch || !gameState || gameState.winner !== null) {
        updateStatus();
        p1Select.disabled = false;
        p2Select.disabled = false;
        return;
    }
    
    await fetchValidMoves();
    await updateWinProbability();
    renderBoard();
    updateStatus();

    const isP1Turn = gameState.current_player === P1;
    const currentConfig = isP1Turn ? p1Select.value : p2Select.value;
    
    if (currentConfig !== "human") {
        // It's a bot's turn
        requestBotMove(currentConfig);
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

    let allowedDestinations = [];
    if (selectedPiece) {
        const startKey = `${selectedPiece.r},${selectedPiece.c}`;
        if (validDestinationsMap[startKey]) {
            allowedDestinations = validDestinationsMap[startKey].map(m => `${m.end[0]},${m.end[1]}`);
        }
    }

    // Always render with Red at the bottom (Standard Orientation)
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
                
                // Color mapping
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
    
    const isP1Turn = gameState.current_player === P1;
    const currentConfig = isP1Turn ? p1Select.value : p2Select.value;
    
    // Validate human turn
    if(currentConfig !== "human") return;
    
    const pID = gameState.current_player;

    const pieceVal = gameState.board[r][c];
    
    // Selecting own piece
    if ((pID === P1 && (pieceVal === P1 || pieceVal === P1_KING)) || 
        (pID === P2 && (pieceVal === P2 || pieceVal === P2_KING))) {
            
        // Deselect if already selected
        if (selectedPiece && selectedPiece.r === r && selectedPiece.c === c) {
            selectedPiece = null;
            renderBoard();
            return;
        }

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
        checkAndExecuteTurn();
    } catch (err) {
        console.error("Move request failed", err);
    }
}

async function requestBotMove(botId) {
    loadingOverlay.classList.remove('hidden');
    statusText.textContent = "Bot is thinking...";
    
    const temperature = parseFloat(tempSlider.value);
    const searchDepth = parseInt(depthSlider.value);
    
    try {
        const payload = { 
            state: gameState, 
            temperature: temperature,
            bot_id: botId,
            search_depth: searchDepth
        };
        const response = await fetch(`${API_URL}/bot-move`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
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
            checkAndExecuteTurn();
        }, 500);

    } catch (err) {
        console.error("Bot AI error", err);
        loadingOverlay.classList.add('hidden');
        statusText.textContent = "Bot Error";
    }
}

function updateStatus() {
    let prefix = currentHistoryIndex !== stateHistory.length - 1 ? "[REVIEW] " : "";
    
    if (gameState.winner === P1) {
        statusText.textContent = prefix + "Red Wins! 🎉";
        statusText.style.color = "#ff3366";
    } else if (gameState.winner === P2) {
        statusText.textContent = prefix + "White Wins! 🤖";
        statusText.style.color = "#e0e0e0";
    } else {
        const turnText = gameState.current_player === P1 ? "Red's Turn" : "White's Turn";
        statusText.textContent = prefix + turnText;
        statusText.style.color = "var(--text-secondary)";
    }
}
