import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import matplotlib.pyplot as plt
from core.ai_model import PerformanceModel

def generate_data(num_samples=1000):
    X = np.random.rand(num_samples, 3).astype(np.float32)
    y = []
    for sample in X:
        score = (sample[0] * 0.5) + (sample[1] * 0.3) + (sample[2] * 0.2)
        y.append([1.0 if score > 0.5 else 0.0])
    return torch.tensor(X), torch.tensor(y, dtype=torch.float32)

def train():
    model = PerformanceModel()
    criterion = nn.BCELoss()
    optimizer = optim.Adam(model.parameters(), lr=0.01)
    
    X, y = generate_data()
    
    epochs = 100
    losses = []
    
    for epoch in range(epochs):
        optimizer.zero_grad()
        outputs = model(X)
        loss = criterion(outputs, y)
        loss.backward()
        optimizer.step()
        
        losses.append(loss.item())
        if (epoch+1) % 10 == 0:
            print(f'Epoch [{epoch+1}/{epochs}], Loss: {loss.item():.4f}')

    plt.figure(figsize=(10, 5))
    plt.plot(losses, label='Training Loss')
    plt.title('Model Training Progress (Loss Curve)')
    plt.xlabel('Epochs')
    plt.ylabel('Loss')
    plt.legend()
    plt.savefig('training_loss.png')
    
    torch.save(model.state_dict(), 'core/trained_model.pth')
    print("Training complete. Graph saved as training_loss.png")

if __name__ == "__main__":
    train()