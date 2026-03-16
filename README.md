# Checkers Deep Learning API & App

This project uses a Neural Network guided by Monte Carlo Tree Search (MCTS) to play Checkers. The AI is wrapped in a FastAPI backend with a sleek HTML/JS/CSS frontend to let users interactively play and adjust the AI's "creativity" (softmax sampling temperature).

## Architecture
- **Backend Model**: Custom ResNet style PyTorch model outputting a Policy (move probabilities) and a Value (win likelihood estimation).
- **Search Algorithm**: MCTS algorithm mapping possible future states and utilizing the Neural Network as a heuristic scoring function at the leaf nodes.
- **Backend API**: A fast, asynchronous state management server built using Python `FastAPI`. 
- **Frontend App**: Pure HTML, Vanilla CSS, and JS components providing an interactive, glassmorphism UI board.

## Getting Started Locally

You can run this full-stack application easily via Docker.
1. Git clone this repository: `https://github.com/Requiar/Checkers-Deep-Learning.git`
2. Assure that you have Docker Desktop (or the Docker daemon) running.
3. In the root directory, simply run:
```bash
docker-compose up --build
```
4. Then navigate to [http://localhost:8080](http://localhost:8080) in your web browser.

## The Temperature Slider ($\tau$)
The frontend contains an adjustable slider for the Bot Temperature ($\tau$). In standard logic, a bot would always choose the highest probability move determined by the search algorithm (a greedy choice, where $\tau$ approaches $0$). 

By sliding this value above 0.5 (or higher), the bot utilizes softmax distribution over its search tree visit counts to "sample" its moves probabilistically. In effect, high temperature translates to more creative, random, or sub-optimal "exploratory" moves.
