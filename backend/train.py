"""
Real Self-Play Training for Checkers Bots
==========================================
Uses minimax self-play to generate training data, then trains
CNN models on outcome-labeled board states with exponential discounting.

Training pipeline:
  1. Generate N self-play games via minimax (fast with alpha-beta pruning)
  2. Label every board state with the game's outcome
  3. Apply exponential discount: early positions → 0.5, late positions → true label
  4. Train a 2-headed CNN (policy + value) on the labeled data
  5. Repeat for each bot configuration with different hyperparameters
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader, random_split
import numpy as np
import json
import os
import random

from backend.model import CheckersNet
from backend.checkers_logic import CheckersEnvironment, P1, P2, P1_KING, P2_KING, EMPTY
from backend.minimax import get_best_move_minimax
from backend.mcts import encode_board
from backend.ranking import EloRanking


# ─── Self-Play Data Generation ───────────────────────────────────────────

def generate_self_play_game(depth=3, temperature=1.0, max_moves=150):
    """
    Play a complete game via minimax self-play and collect all board states.
    Returns list of (state_dict, outcome_label).
    """
    env = CheckersEnvironment()
    history = []
    move_count = 0
    
    while env.winner is None and move_count < max_moves:
        valid_moves = env.get_valid_moves()
        if not valid_moves:
            break
        
        # Record the board state BEFORE making the move
        history.append({
            "board": [row[:] for row in env.board],
            "current_player": env.current_player
        })
        
        move = get_best_move_minimax(env, depth=depth, temperature=temperature)
        if move is None:
            break
        
        env.make_move(move)
        move_count += 1
    
    # Determine outcome
    if env.winner == P1:
        label = 1.0    # Red/P1 won
    elif env.winner == P2:
        label = -1.0   # White/P2 won
    else:
        label = 0.0    # Draw
    
    return history, label, move_count


def generate_dataset(num_games, depth=3, temperature=1.0, max_moves=150):
    """
    Generate a dataset of self-play games.
    Returns list of (state_dict, raw_label, distance_from_end).
    """
    all_samples = []
    wins = {P1: 0, P2: 0, "draw": 0}
    
    for i in range(num_games):
        history, label, move_count = generate_self_play_game(
            depth=depth, temperature=temperature, max_moves=max_moves
        )
        
        T = len(history)
        for t, state in enumerate(history):
            distance = T - 1 - t  # Distance from end of game
            all_samples.append((state, label, distance))
        
        if label == 1.0:
            wins[P1] += 1
        elif label == -1.0:
            wins[P2] += 1
        else:
            wins["draw"] += 1
        
        if (i + 1) % 10 == 0 or (i + 1) == num_games:
            print(f"  Generated {i+1}/{num_games} games ({len(all_samples)} states) "
                  f"[P1: {wins[P1]}, P2: {wins[P2]}, Draw: {wins['draw']}]")
    
    return all_samples


# ─── PyTorch Dataset ─────────────────────────────────────────────────────

class CheckersDataset(Dataset):
    """
    Dataset of labeled checkers board states for CNN training.
    
    Each sample: (5-channel board tensor, value_target)
    
    Exponential label discounting:
        discounted = raw_label * (1 - gamma)^distance
    Where distance = how far from end of game this state was.
    gamma=0: no discounting (all states get the true label)
    gamma close to 1: only endgame states get meaningful labels
    """
    
    def __init__(self, samples, discount_factor=0.0):
        self.entries = []
        
        for state, raw_label, distance in samples:
            discount = (1.0 - discount_factor) ** distance
            discounted_label = raw_label * discount
            
            self.entries.append((state, discounted_label))
    
    def __len__(self):
        return len(self.entries)
    
    def __getitem__(self, idx):
        state, label = self.entries[idx]
        
        # Convert to 5-channel tensor
        board = np.array(state["board"])
        encoded = np.zeros((5, 8, 8), dtype=np.float32)
        encoded[0] = (board == EMPTY).astype(np.float32)
        encoded[1] = (board == P1).astype(np.float32)
        encoded[2] = (board == P2).astype(np.float32)
        encoded[3] = (board == P1_KING).astype(np.float32)
        encoded[4] = (board == P2_KING).astype(np.float32)
        
        tensor = torch.tensor(encoded)
        target = torch.tensor([label], dtype=torch.float32)
        
        return tensor, target


# ─── Training Loop ───────────────────────────────────────────────────────

def train_model(model, train_loader, val_loader, epochs, lr, device="cpu"):
    """
    Train the CheckersNet model on self-play data.
    Uses MSE loss on the value head (predicting game outcome).
    Returns train_losses and val_losses per epoch.
    """
    optimizer = optim.Adam(model.parameters(), lr=lr)
    criterion = nn.MSELoss()
    
    model.to(device)
    train_losses = []
    val_losses = []
    
    for epoch in range(1, epochs + 1):
        # ── Training Phase ──
        model.train()
        epoch_loss = 0.0
        batches = 0
        
        for x, y in train_loader:
            x, y = x.to(device), y.to(device)
            
            _, value = model(x)
            loss = criterion(value, y)
            
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
            epoch_loss += loss.item()
            batches += 1
        
        t_loss = epoch_loss / max(batches, 1)
        train_losses.append(round(t_loss, 4))
        
        # ── Validation Phase ──
        model.eval()
        val_loss = 0.0
        val_batches = 0
        
        with torch.no_grad():
            for x, y in val_loader:
                x, y = x.to(device), y.to(device)
                _, value = model(x)
                loss = criterion(value, y)
                val_loss += loss.item()
                val_batches += 1
        
        v_loss = val_loss / max(val_batches, 1)
        val_losses.append(round(v_loss, 4))
        
        if epoch % 5 == 0 or epoch == epochs or epoch == 1:
            print(f"    Epoch {epoch}/{epochs} — Train: {t_loss:.4f}, Val: {v_loss:.4f}")
    
    return train_losses, val_losses


# ─── Main Training Sweep ─────────────────────────────────────────────────

def run_training_sweep():
    print("=" * 60)
    print("  REAL Self-Play Training Sweep")
    print("=" * 60)
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}\n")
    
    # Bot configurations — each differs in training data volume,
    # model architecture, and training hyperparameters.
    bots_config = {
        "bot_v1_baseline": {
            "num_games": 60,  "gen_depth": 3, "gen_temp": 1.0,
            "epochs": 30, "layers": 4, "channels": 64,
            "batch_size": 32, "dropout": 0.0, "lr": 1e-3, "discount": 0.1
        },
        "bot_v2_deep": {
            "num_games": 80, "gen_depth": 4, "gen_temp": 0.8,
            "epochs": 40, "layers": 6, "channels": 128,
            "batch_size": 64, "dropout": 0.1, "lr": 5e-4, "discount": 0.15
        },
        "bot_v3_fast": {
            "num_games": 40, "gen_depth": 2, "gen_temp": 1.5,
            "epochs": 15, "layers": 2, "channels": 32,
            "batch_size": 16, "dropout": 0.0, "lr": 1e-2, "discount": 0.05
        },
        "bot_v4_dropout": {
            "num_games": 70, "gen_depth": 3, "gen_temp": 0.5,
            "epochs": 35, "layers": 4, "channels": 64,
            "batch_size": 32, "dropout": 0.3, "lr": 1e-3, "discount": 0.2
        },
    }
    
    os.makedirs("backend/models", exist_ok=True)
    metadata = {}
    
    for bot_id, cfg in bots_config.items():
        print(f"\n{'─' * 50}")
        print(f"  Bot: {bot_id}")
        print(f"  Config: {cfg}")
        print(f"{'─' * 50}")
        
        # ── Step 1: Generate self-play data ──
        print(f"\n  Step 1: Generating {cfg['num_games']} self-play games (depth={cfg['gen_depth']}, temp={cfg['gen_temp']})...")
        samples = generate_dataset(
            num_games=cfg["num_games"],
            depth=cfg["gen_depth"],
            temperature=cfg["gen_temp"],
            max_moves=150
        )
        print(f"  Total training samples: {len(samples)}")
        
        if len(samples) < 10:
            print(f"  WARNING: Too few samples for {bot_id}, skipping.")
            continue
        
        # ── Step 2: Create dataset with discounting ──
        dataset = CheckersDataset(samples, discount_factor=cfg["discount"])
        
        # 80/20 train-val split
        train_size = int(0.8 * len(dataset))
        val_size = len(dataset) - train_size
        train_set, val_set = random_split(dataset, [train_size, val_size])
        
        train_loader = DataLoader(train_set, batch_size=cfg["batch_size"], shuffle=True)
        val_loader = DataLoader(val_set, batch_size=cfg["batch_size"])
        
        # ── Step 3: Initialize model ──
        model = CheckersNet(
            num_res_blocks=cfg["layers"],
            channels=cfg["channels"],
            dropout_rate=cfg["dropout"]
        )
        
        # ── Step 4: Train ──
        print(f"\n  Step 2: Training for {cfg['epochs']} epochs...")
        train_losses, val_losses = train_model(
            model, train_loader, val_loader,
            epochs=cfg["epochs"], lr=cfg["lr"], device=device
        )
        
        # ── Step 5: Save weights ──
        weight_path = f"backend/models/{bot_id}.pt"
        torch.save(model.state_dict(), weight_path)
        print(f"  Saved weights → {weight_path}")
        
        metadata[bot_id] = {
            "name": bot_id.replace("_", " ").title(),
            "config": cfg,
            "training_samples": len(samples),
            "final_train_loss": train_losses[-1],
            "final_val_loss": val_losses[-1],
            "train_losses": train_losses,
            "val_losses": val_losses,
            "weight_path": weight_path
        }
    
    # ── Add Random Bot baseline ──
    metadata["bot_random"] = {
        "name": "Random Move Bot",
        "config": {"epochs": 0, "layers": 0, "channels": 0, "batch_size": 0,
                   "dropout": 0, "lr": 0, "discount": 0},
        "training_samples": 0,
        "final_train_loss": 0.0,
        "final_val_loss": 0.0,
        "train_losses": [],
        "val_losses": [],
        "weight_path": None
    }
    
    # ── Save catalog ──
    with open("backend/models/catalog.json", "w") as f:
        json.dump(metadata, f, indent=4)
    print(f"\nSaved catalog for {len(metadata)} bots.")
    
    # ── Initialize Elo ratings ──
    ranking = EloRanking(alpha=0.01)
    for bot_id in metadata.keys():
        if bot_id == "bot_random":
            ranking.set_rating(bot_id, 800)
        else:
            ranking.set_rating(bot_id, 1000)
    ranking.save("backend/elo_ratings.json")
    print("Initialized Elo ratings.")
    
    print("\n" + "=" * 60)
    print("  Training sweep complete!")
    print("=" * 60)


if __name__ == "__main__":
    run_training_sweep()
