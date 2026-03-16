import math
import numpy as np
import json

class EloRanking:
    """
    Implements a continuous rating ranking system based on the Bradley-Terry model.
    The probability of player i beating player j is a logistic function of the difference
    in their skill ratings:
    
    P(i wins) = sigmoid(alpha * (r_i - r_j))
    
    where alpha is a scaling constant (often 1.0 or derived from standard Elo math).
    """
    def __init__(self, alpha=1.0, k_factor=32):
        self.alpha = alpha
        self.k_factor = k_factor
        self.ratings = {} # Dictionary mapping player_id -> rating

    def get_rating(self, player_id):
        return self.ratings.get(player_id, 1000.0) # Default rating is 1000
    
    def set_rating(self, player_id, rating):
        self.ratings[player_id] = rating
        
    def expected_win_probability(self, rating_i, rating_j):
        """
        Sigmoid probability of i beating j based on lecture notes:
        P(i wins, j loses) = sigmoid(alpha * (r_i - r_j))
        
        Using a standard logistic curve: 1 / (1 + e^-(x))
        """
        x = self.alpha * (rating_i - rating_j)
        # To match standard Elo scaling, we often use base 10, but the lecture formulation 
        # specifies a generic alpha * (r_i - r_j) inside a sigmoid \sigma.
        # \sigma(z) = 1 / (1 + exp(-z))
        
        # Prevent overflow for very large rating differences
        if x > 500:
            return 1.0
        elif x < -500:
            return 0.0
            
        return 1.0 / (1.0 + math.exp(-x))
        
    def update_ratings(self, player_i, player_j, outcome_i):
        """
        Updates ratings after a match.
        outcome_i: 1 if player_i wins, 0 if player_i loses, 0.5 for a draw.
        """
        r_i = self.get_rating(player_i)
        r_j = self.get_rating(player_j)
        
        # Compute expected probabilities using Bradley-Terry model (logistic function)
        p_i_wins = self.expected_win_probability(r_i, r_j)
        p_j_wins = 1.0 - p_i_wins # Equivalent to expected_win_probability(r_j, r_i)
        
        # Update rule
        # new_rating = old_rating + K * (Actual - Expected)
        new_r_i = r_i + self.k_factor * (outcome_i - p_i_wins)
        
        # Outcome for j is 1 - outcome_i
        outcome_j = 1.0 - outcome_i
        new_r_j = r_j + self.k_factor * (outcome_j - p_j_wins)
        
        self.set_rating(player_i, new_r_i)
        self.set_rating(player_j, new_r_j)
        
    def save(self, path="backend/elo_ratings.json"):
        with open(path, "w") as f:
            json.dump(self.ratings, f, indent=4)
            
    def load(self, path="backend/elo_ratings.json"):
        try:
            with open(path, "r") as f:
                self.ratings = json.load(f)
        except FileNotFoundError:
            self.ratings = {}

# Example Usage Evaluation (Demonstrates logic mathematically maps to lecture)
if __name__ == "__main__":
    # Standard Elo alpha is often ln(10)/400 config to map linearly to standard chess rating
    # But for a raw sigmoid with alpha=0.01:
    ranking = EloRanking(alpha=0.01)
    
    ranking.set_rating("Model_A", 1200)
    ranking.set_rating("Model_B", 1000)
    
    print(f"Initial Ratings: A={ranking.get_rating('Model_A')}, B={ranking.get_rating('Model_B')}")
    prob_A_wins = ranking.expected_win_probability(1200, 1000)
    print(f"Probability A wins (by Formula): {prob_A_wins:.4f}")
    
    print("\nSimulating A winning...")
    ranking.update_ratings("Model_A", "Model_B", outcome_i=1.0)
    print(f"New Ratings: A={ranking.get_rating('Model_A'):.2f}, B={ranking.get_rating('Model_B'):.2f}")
    
    print("\nSimulating B winning...")
    ranking.update_ratings("Model_A", "Model_B", outcome_i=0.0)
    print(f"New Ratings: A={ranking.get_rating('Model_A'):.2f}, B={ranking.get_rating('Model_B'):.2f}")
