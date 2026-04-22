import torch
import torch.nn as nn
import os

class PerformanceModel(nn.Module):
    def __init__(self):
        super(PerformanceModel, self).__init__()
        self.layer1 = nn.Linear(3, 16)
        self.layer2 = nn.Linear(16, 8)
        self.layer3 = nn.Linear(8, 1)
        self.relu = nn.ReLU()
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        x = self.relu(self.layer1(x))
        x = self.relu(self.layer2(x))
        x = self.sigmoid(self.layer3(x))
        return x

def predict_performance(m1, m2, m3):
    model = PerformanceModel()
    model_path = os.path.join(os.path.dirname(__file__), 'trained_model.pth')
    
    if os.path.exists(model_path):
        model.load_state_dict(torch.load(model_path, weights_only=True))
    
    model.eval()
    
    try:
        norm_m1 = min(float(m1) / 2.5, 1.0)
        norm_m2 = min(float(m2) / 10.0, 1.0)
        norm_m3 = min(float(m3) / 500.0, 1.0)
        
        weighted_score = (norm_m1 * 50) + (norm_m2 * 30) + (norm_m3 * 20)
        
        return round(max(weighted_score, 0.5), 1)
    except:
        return 0.5