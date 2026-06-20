import os
import django
import numpy as np
import joblib
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import train_test_split

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_project.settings')
django.setup()

from core.models import DailyStatSnapshot, TrackedPlayer

def load_hypixel_data():
    print("Loading database records (this may take a few seconds)...")
    all_snaps = DailyStatSnapshot.objects.all()
    if not all_snaps.exists():
        print("No training data found! Please wait for daily_scraper.py to collect data.")
        return None, None
        
    X_data, y_data = [], []
    
    print("Calculating metrics...")
    max_sb_xp = 50000.0
    max_combat = 111672425.0
    max_cata = 5698096400.0
    max_mining = 111672425.0
    max_farming = 111672425.0
    max_foraging = 111672425.0
    max_fishing = 111672425.0

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
            ca_gain = (last.catacombs_xp - first.catacombs_xp) / days_diff
            mi_gain = (last.mining_xp - first.mining_xp) / days_diff
            fa_gain = (last.farming_xp - first.farming_xp) / days_diff
            fo_gain = (last.foraging_xp - first.foraging_xp) / days_diff
            fi_gain = (last.fishing_xp - first.fishing_xp) / days_diff
            
            x_m1 = min(last.skyblock_xp / max_sb_xp, 1.0)
            x_m2 = min(last.combat_xp / max_combat, 1.0)
            x_m3 = min(last.catacombs_xp / max_cata, 1.0)
            x_m4 = min(last.mining_xp / max_mining, 1.0)
            x_m5 = min(last.farming_xp / max_farming, 1.0)
            x_m6 = min(last.foraging_xp / max_foraging, 1.0)
            x_m7 = min(last.fishing_xp / max_fishing, 1.0)
            x_m8 = 0.0
            
            y_m1 = max(0.0, min((sb_gain * 7) / max_sb_xp, 1.0))
            y_m2 = max(0.0, min((cb_gain * 7) / max_combat, 1.0))
            y_m3 = max(0.0, min((ca_gain * 7) / max_cata, 1.0))
            y_m4 = max(0.0, min((mi_gain * 7) / max_mining, 1.0))
            y_m5 = max(0.0, min((fa_gain * 7) / max_farming, 1.0))
            y_m6 = max(0.0, min((fo_gain * 7) / max_foraging, 1.0))
            y_m7 = max(0.0, min((fi_gain * 7) / max_fishing, 1.0))
            y_m8 = 0.0
            
            X_data.append([x_m1, x_m2, x_m3, x_m4, x_m5, x_m6, x_m7, x_m8])
            y_data.append([y_m1, y_m2, y_m3, y_m4, y_m5, y_m6, y_m7, y_m8])
            
    if len(X_data) == 0:
        print("Not enough players with multiple days of data to train a forecaster.")
        return None, None

    print(f"Successfully loaded {len(X_data)} players for training!")
    return np.array(X_data), np.array(y_data)

def train():
    X, y = load_hypixel_data()
    if X is None:
        return
    
    print("Training Random Forest Forecaster...")
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    model.fit(X_train, y_train)
    preds = model.predict(X_test)
    mse = mean_squared_error(y_test, preds)
    print(f"Evaluation complete! Realistic Test Mean Squared Error: {mse:.6f}")
    
    model.fit(X, y)
    joblib.dump(model, 'core/trained_rf_model.joblib')
    print("Model saved as core/trained_rf_model.joblib")

if __name__ == "__main__":
    train()