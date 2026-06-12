import os
import django
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import matplotlib.pyplot as plt

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_project.settings')
django.setup()

from core.ai_model import PerformanceModel
from core.models import DailyStatSnapshot, TrackedPlayer

def load_hypixel_data():
    print("Loading database records (this may take a few seconds)...")
    all_snaps = DailyStatSnapshot.objects.all()
    if not all_snaps.exists():
        print("No training data found! Please wait for daily_scraper.py to collect data.")
        return None, None
        
    X_data, y_data = [], []
    
    print("Calculating metrics...")
    max_sb_xp = max(all_snaps.values_list('skyblock_xp', flat=True)) or 1
    max_combat = max(all_snaps.values_list('combat_xp', flat=True)) or 1
    max_wealth = max(all_snaps.values_list('bank_balance', flat=True)) or 1

    print("Formatting player progression data...")
    all_snaps_list = list(all_snaps.order_by('player_id', 'date'))
    player_groups = {}
    
    for snap in all_snaps_list:
        if snap.player_id not in player_groups:
            player_groups[snap.player_id] = []
        player_groups[snap.player_id].append(snap)

    active_player_ids = set(TrackedPlayer.objects.filter(is_active=True).values_list('id', flat=True))
    for p_id, snaps in player_groups.items():
        if p_id in active_player_ids and len(snaps) >= 2:
            first = snaps[0]
            last = snaps[-1]
            
            days_diff = (last.date - first.date).days
            if days_diff <= 0:
                continue
                
            sb_gain = (last.skyblock_xp - first.skyblock_xp) / days_diff
            cb_gain = (last.combat_xp - first.combat_xp) / days_diff
            wl_gain = (last.bank_balance - first.bank_balance) / days_diff
            
            x_m1 = min(last.skyblock_xp / max_sb_xp, 1.0)
            x_m2 = min(last.combat_xp / max_combat, 1.0)
            x_m3 = min(last.bank_balance / max_wealth, 1.0)
            
            y_m1 = min((last.skyblock_xp + (sb_gain * 7)) / max_sb_xp, 1.0)
            y_m2 = min((last.combat_xp + (cb_gain * 7)) / max_combat, 1.0)
            y_m3 = min((last.bank_balance + (wl_gain * 7)) / max_wealth, 1.0)
            
            X_data.append([x_m1, x_m2, x_m3])
            y_data.append([y_m1, y_m2, y_m3])
            
    if len(X_data) == 0:
        print("Not enough players with multiple days of data to train a forecaster.")
        return None, None

    print(f"Successfully loaded {len(X_data)} players for training!")
    return torch.tensor(X_data, dtype=torch.float32), torch.tensor(y_data, dtype=torch.float32)

def train():
    X, y = load_hypixel_data()
    if X is None:
        return
    
    model = PerformanceModel()
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=0.01)
    
    epochs = 150
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