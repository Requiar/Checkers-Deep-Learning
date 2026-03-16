import torch
from backend.model import CheckersNet

def generate_dummy_weights(path="backend/model.pt"):
    print("Generating dummy model weights...")
    model = CheckersNet()
    # In a real scenario, this is where we'd run thousands of self-play games
    # For now, we just save the randomly initialized model so the API can load it.
    torch.save(model.state_dict(), path)
    print(f"Saved dummy weights to {path}")

if __name__ == "__main__":
    generate_dummy_weights()
