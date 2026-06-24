import os
import django
import sys

# Setup django
sys.path.append(r'c:\Users\aleem_rmv7k3n\Documents\FYP')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_project.settings')
django.setup()

from core.models import SavedGame, User
from core.views import GAME_REGISTRY
from core.integrations import get_euclidean_similarity

def debug_recommendations():
    # Pick a random user that has a saved game
    try:
        user = SavedGame.objects.first().user
    except:
        print("No saved games exist.")
        return
        
    print(f"Testing recommendations for user: {user.username}")
    
    user_games = SavedGame.objects.filter(user=user).order_by('date_saved')
    all_other_games = SavedGame.objects.exclude(user=user).select_related('user').order_by('-date_saved')[:100]
    
    print(f"Found {user_games.count()} user games.")
    print(f"Found {all_other_games.count()} other games.")
    
    recommendations = []
    if user_games.exists():
        for my_game in user_games:
            my_integration = GAME_REGISTRY.get(my_game.platform)
            if not my_integration: 
                print(f"Missing integration for {my_game.platform}")
                continue
            
            my_vec = my_integration.get_comparison_vector({
                "m1": my_game.m1 or 0, "m2": my_game.m2 or 0, "m3": my_game.m3 or 0
            })
            
            for other in all_other_games:
                if other.platform != my_game.platform:
                    continue
                    
                other_integration = GAME_REGISTRY.get(other.platform)
                if not other_integration: continue
                
                other_vec = other_integration.get_comparison_vector({
                    "m1": other.m1 or 0, "m2": other.m2 or 0, "m3": other.m3 or 0
                })
                
                sim = get_euclidean_similarity(my_vec, other_vec)
                
                rec = {
                    'username': other.user.username, 'game_name': other.game_username,
                    'score': sim, 'platform': other.platform
                }
                recommendations.append(rec)
                print(f"Match: {my_game.platform} -> {other.platform} | Score: {sim}")
                
    unique_recs = {}
    for rec in sorted(recommendations, key=lambda x: x['score'], reverse=True):
        if rec['username'] not in unique_recs:
            unique_recs[rec['username']] = rec
            
    final_recommendations = list(unique_recs.values())[:5]
    print(f"Final recommendations: {final_recommendations}")

if __name__ == '__main__':
    debug_recommendations()
