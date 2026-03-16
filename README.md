# Checkers Deep Learning API & App

This project uses a Neural Network guided by Monte Carlo Tree Search (MCTS) to play Checkers. The AI is wrapped in a FastAPI backend with a sleek HTML/JS/CSS frontend to let users interactively play and adjust the AI's "creativity" (softmax sampling temperature).

## Architecture
- **Backend Model**: Custom ResNet style PyTorch model outputting a Policy (move probabilities) and a Value (win likelihood estimation).
- **Search Algorithm**: MCTS algorithm mapping possible future states and utilizing the Neural Network as a heuristic scoring function at the leaf nodes.
- **Backend API**: A fast, asynchronous state management server built using Python `FastAPI`. 
- **Frontend App**: Pure HTML, Vanilla CSS, and JS components providing an interactive, glassmorphism UI board with a premium "Noir" dark aesthetic.

## Features
- **Play vs AI**: Challenge deep-learning models trained via self-play.
- **Adjustable Creativity ($\tau$)**: Shift the softmax temperature slider to force the AI to sample sub-optimal, exploratory moves.
- **Search Depth Control**: Dynamically adjust the number of MCTS simulations the model performs per turn.
- **AI Tournaments**: Pit different models against each other in batch mode to see them battle for Elo rating supremacy. Fast-forward through matches and view live standings.
- **Dual Engine Evaluation**: Watch models play against each other with real-time, side-by-side "Win Probability" evaluation bars showing each engine's opinion of the board.
- **Model Details**: Inspect the hyperparameters, architecture, and training losses of the available models in the catalog.

## Getting Started Locally

You can run this full-stack application easily via Docker.
1. Git clone this repository.
2. Assure that you have Docker Desktop (or the Docker daemon) running.
3. In the root directory, simply run:
```bash
docker-compose up --build
```
4. Then navigate to [http://localhost:8080](http://localhost:8080) in your web browser.
