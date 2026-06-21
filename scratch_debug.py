import os
import django
import joblib

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_project.settings')
django.setup()

from core.models import CrowdsourcedStatSnapshot
from core.integrations import GAME_REGISTRY
from core.ai_model import predict_performance

username = 'aleemo'
game_choice = 'hypixel'

snapshots = CrowdsourcedStatSnapshot.objects.filter(game_choice=game_choice, username=username).order_by('date')
print(f"Snapshots for {username}: {snapshots.count()}")
if snapshots.count() > 0:
    for s in snapshots:
        print(f"Date: {s.date}, m1: {s.m1}, m2: {s.m2}, m3: {s.m3}")
    
    last = snapshots.last()
    stats_data = {
        'm1': last.m1, 'm2': last.m2, 'm3': last.m3, 'm4': last.m4, 
        'm5': last.m5, 'm6': last.m6, 'm7': last.m7, 'm8': last.m8
    }
    
    integration = GAME_REGISTRY.get(game_choice)
    norms = integration.get_insights(stats_data)['norms']
    print(f"Norms: {norms}")
    
    prediction = predict_performance(norms, game_choice)
    print(f"Raw Prediction dict: {prediction}")
    
    futures = integration.calculate_future(stats_data, prediction, [60000.0, 111672425.0, 569809640.0, 111672425.0, 111672425.0, 111672425.0, 111672425.0, 0.0])
    print(f"Futures (Absolute XP): {futures}")
    
    for i, max_val in enumerate([60000.0, 111672425.0, 569809640.0, 111672425.0, 111672425.0, 111672425.0, 111672425.0, 0.0]):
        current = getattr(last, f'm{i+1}')
        print(f"m{i+1} Growth: {futures[i] - current} XP in 7 days")
