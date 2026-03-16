import torch
from backend.model import CheckersNet
from backend.ranking import EloRanking

def generate_dummy_weights(path="backend/model.pt"):
    print("Generating dummy model weights...")
    model = CheckersNet()
    # In a real scenario, this is where we'd run thousands of self-play games
    # For now, we just save the randomly initialized model so the API can load it.
    torch.save(model.state_dict(), path)
    print(f"Saved dummy weights to {path}")
    
    # Demonstrate Bradley-Terry Mathematical constraints mathematically
    print("--- \nDemonstrating Lecture Note constraints on Ranking/Elo... ")
    ranking = EloRanking(alpha=0.01) # alpha scaling constant from lecture notes
    ranking.set_rating("Model_v1", 1200)
    ranking.set_rating("Model_Random", 1000)
    
    p_v1_wins = ranking.expected_win_probability(1200, 1000)
    print(f"Prob. v1 wins over Random: {p_v1_wins:.4f} (Sigmoid of alpha * (r_i - r_j))")
    
    # Simulate a win for v1
    ranking.update_ratings("Model_v1", "Model_Random", outcome_i=1.0)
    print(f"After win - v1 Elo: {ranking.get_rating('Model_v1'):.2f}, Random Elo: {ranking.get_rating('Model_Random'):.2f}")


if __name__ == "__main__":
    generate_dummy_weights()
