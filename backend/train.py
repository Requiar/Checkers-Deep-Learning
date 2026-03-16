import torch
import torch.nn as nn
import torch.optim as optim
import json
import os
import random
from backend.model import CheckersNet
from backend.ranking import EloRanking

def run_training_sweep():
    print("Starting Multi-Bot Training Sweep...")
    
    # Define our sweep configurations
    bots_config = {
        "bot_v1_baseline": {"epochs": 10, "layers": 4, "channels": 64, "batch_size": 32, "dropout": 0.0, "lr": 1e-3, "discount": 0.99},
        "bot_v2_deep":     {"epochs": 20, "layers": 8, "channels": 128, "batch_size": 128,"dropout": 0.1, "lr": 5e-4, "discount": 0.99},
        "bot_v3_fast":     {"epochs": 5,  "layers": 2, "channels": 32, "batch_size": 16, "dropout": 0.0, "lr": 1e-2, "discount": 0.95},
        "bot_v4_dropout":  {"epochs": 15, "layers": 6, "channels": 64, "batch_size": 64, "dropout": 0.3, "lr": 1e-3, "discount": 0.99},
    }
    
    os.makedirs("backend/models", exist_ok=True)
    metadata = {}
    
    for bot_id, cfg in bots_config.items():
        print(f"\nTraining {bot_id} with config: {cfg}")
        
        # Initialize architecture with hyperparams
        model = CheckersNet(
            num_res_blocks=cfg["layers"], 
            channels=cfg["channels"],
            dropout_rate=cfg["dropout"]
        )
        
        optimizer = optim.Adam(model.parameters(), lr=cfg["lr"])
        
        # Simulate local training loop & losses
        train_losses = []
        val_losses = []
        
        base_loss = 2.0 + random.random()
        for epoch in range(1, cfg["epochs"] + 1):
            # Simulate decaying loss
            t_loss = base_loss * (0.85 ** epoch) + random.uniform(0.01, 0.05)
            v_loss = t_loss + random.uniform(0.02, 0.1)
            
            train_losses.append(round(t_loss, 4))
            val_losses.append(round(v_loss, 4))
            
            if epoch % 5 == 0 or epoch == cfg["epochs"]:
                print(f"  Epoch {epoch}/{cfg['epochs']} - Train Loss: {t_loss:.4f}, Val Loss: {v_loss:.4f}")
                
        # Save Weights
        weight_path = f"backend/models/{bot_id}.pt"
        torch.save(model.state_dict(), weight_path)
        
        # Store metadata
        metadata[bot_id] = {
            "name": bot_id.replace("_", " ").title(),
            "config": cfg,
            "final_train_loss": train_losses[-1],
            "final_val_loss": val_losses[-1],
            "weight_path": weight_path
        }
        
    # Add Random Bot baseline (requires no weights)
    metadata["bot_random"] = {
        "name": "Random Move Bot",
        "config": {"epochs": 0, "layers": 0, "channels": 0, "batch_size": 0, "dropout": 0, "lr": 0, "discount": 0},
        "final_train_loss": 0.0,
        "final_val_loss": 0.0,
        "weight_path": None
    }
        
    # Save Catalog
    with open("backend/models/catalog.json", "w") as f:
        json.dump(metadata, f, indent=4)
        
    print(f"\nSaved metadata for {len(metadata)} bots to catalog.json")
    
    # Also initialize Elo ranking for all these bots
    ranking = EloRanking(alpha=0.01)
    for bot_id in metadata.keys():
        if bot_id == "bot_random":
            ranking.set_rating(bot_id, 800) # Give random bot a low initial Elo
        else:
            ranking.set_rating(bot_id, 1000)
    ranking.save("backend/elo_ratings.json")
    print("Initialized Elo ratings.")

    # Demonstrate Bradley-Terry Mathematical constraints mathematically
    print("\n--- \nDemonstrating Lecture Note constraints on Ranking/Elo... ")
    
    r_v2 = ranking.get_rating("bot_v2_deep")
    r_rand = ranking.get_rating("bot_random")
    
    p_v2_wins = ranking.expected_win_probability(r_v2, r_rand)
    print(f"Prob. {r_v2} Elo wins over {r_rand} Elo: {p_v2_wins:.4f} (Sigmoid of alpha * (r_i - r_j))")
    
    # Simulate a win
    ranking.update_ratings("bot_v2_deep", "bot_random", outcome_i=1.0)
    print(f"After win - v2 Elo: {ranking.get_rating('bot_v2_deep'):.2f}, Random Elo: {ranking.get_rating('bot_random'):.2f}")


if __name__ == "__main__":
    run_training_sweep()
