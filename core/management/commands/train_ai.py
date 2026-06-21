import os
import numpy as np
import joblib
from django.core.management.base import BaseCommand
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import train_test_split
from core.models import CrowdsourcedStatSnapshot
from core.integrations import GAME_REGISTRY

class Command(BaseCommand):
    help = 'Train the Random Forest model for a specific game based on crowdsourced data.'

    def add_arguments(self, parser):
        parser.add_argument('game', type=str, help='The game_choice to train (e.g. hypixel, fortnite, clash, steam)')

    def handle(self, *args, **options):
        game_choice = options['game']
        self.stdout.write(f"Training AI for {game_choice}...")
        
        integration = GAME_REGISTRY.get(game_choice)
        if not integration:
            self.stdout.write(self.style.ERROR(f"Game '{game_choice}' not found in GAME_REGISTRY!"))
            return
        
        all_snaps = CrowdsourcedStatSnapshot.objects.filter(game_choice=game_choice).order_by('username', 'date')
        if not all_snaps.exists():
            self.stdout.write(self.style.ERROR(f"No training data found for {game_choice}!"))
            return
            
        X_data, y_data = [], []
        
        player_groups = {}
        for snap in all_snaps:
            if snap.username not in player_groups:
                player_groups[snap.username] = []
            player_groups[snap.username].append(snap)
            
        for username, snaps in player_groups.items():
            if len(snaps) >= 2:
                first = snaps[0]
                last = snaps[-1]
                
                days_diff = (last.date - first.date).days
                if days_diff <= 0:
                    continue
                    
                first_stats = {'m1': first.m1, 'm2': first.m2, 'm3': first.m3, 'm4': first.m4, 'm5': first.m5, 'm6': first.m6, 'm7': first.m7, 'm8': first.m8}
                last_stats = {'m1': last.m1, 'm2': last.m2, 'm3': last.m3, 'm4': last.m4, 'm5': last.m5, 'm6': last.m6, 'm7': last.m7, 'm8': last.m8}
                
                game_max_vals = {
                    'hypixel': [60000.0, 111672425.0, 569809640.0, 111672425.0, 111672425.0, 111672425.0, 111672425.0, 0.0],
                    'fortnite': [5.0, 20.0, 1000.0],
                    'clash': [16.0, 5000.0, 2000.0]
                }
                max_vals = game_max_vals.get(game_choice, [1.0]*8)
                
                norms_first = integration.normalize_metrics(first_stats, max_vals)
                norms_last = integration.normalize_metrics(last_stats, max_vals)
                
                x_vec_first = [min(float(n) / 10.0, 1.0) for n in norms_first]
                x_vec_first += [0.0] * (8 - len(x_vec_first))
                
                x_vec_last = [min(float(n) / 10.0, 1.0) for n in norms_last]
                x_vec_last += [0.0] * (8 - len(x_vec_last))
                
                # Predict 7 days in the future (difference)
                y_vec = []
                for i in range(8):
                    diff = x_vec_last[i] - x_vec_first[i]
                    growth_7_days = (diff / days_diff) * 7
                    y_vec.append(max(0.0, min(growth_7_days, 1.0)))
                
                X_data.append(x_vec_last)
                y_data.append(y_vec)
                
        if len(X_data) < 5:
            self.stdout.write(self.style.ERROR(f"Not enough players with multiple days of data ({len(X_data)}) to train a forecaster."))
            return
            
        X = np.array(X_data)
        y = np.array(y_data)
        
        self.stdout.write(f"Successfully loaded {len(X_data)} players. Training Random Forest...")
        model = RandomForestRegressor(n_estimators=100, random_state=42)
        
        try:
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            model.fit(X_train, y_train)
            preds = model.predict(X_test)
            mse = mean_squared_error(y_test, preds)
            self.stdout.write(self.style.SUCCESS(f"Evaluation complete! Realistic Test Mean Squared Error: {mse:.6f}"))
        except ValueError:
            self.stdout.write(self.style.WARNING("Not enough data to split for evaluation. Training on full dataset."))

        model.fit(X, y)
        model_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), f'trained_rf_model_{game_choice}.joblib')
        joblib.dump(model, model_path)
        self.stdout.write(self.style.SUCCESS(f"Model saved as core/trained_rf_model_{game_choice}.joblib"))
