import os
import numpy as np
import joblib
from .models import CrowdsourcedStatSnapshot
from django.db.models import Count
from django.core.mail import mail_admins

_MODEL_CACHE = {}

def get_model(game_choice):
    global _MODEL_CACHE
    if game_choice not in _MODEL_CACHE:
        model_path = os.path.join(os.path.dirname(__file__), f'trained_rf_model_{game_choice}.joblib')
        if os.path.exists(model_path):
            _MODEL_CACHE[game_choice] = joblib.load(model_path)
        else:
            _MODEL_CACHE[game_choice] = None
    return _MODEL_CACHE[game_choice]

def predict_performance(norms, game_choice='hypixel'):
    model = get_model(game_choice)
    
    if not model:
        try:
            eligible_users = CrowdsourcedStatSnapshot.objects.filter(game_choice=game_choice).values('username').annotate(snap_count=Count('id')).filter(snap_count__gte=2).count()
            
            if eligible_users >= 100:
                from django.core.cache import cache
                from django.contrib.auth.models import User
                from django.core.mail import send_mail
                from django.conf import settings
                
                cache_key = f"training_email_sent_{game_choice}"
                if not cache.get(cache_key):
                    # Dynamically get all registered admins from the database
                    admin_emails = list(User.objects.filter(is_superuser=True).values_list('email', flat=True))
                    valid_emails = [e for e in admin_emails if e]
                    
                    if valid_emails:
                        send_mail(
                            subject=f"AI Ready for Training: {game_choice}",
                            message=f"The game '{game_choice}' has reached 100 eligible users.\nRun 'python manage.py train_ai {game_choice}'.",
                            from_email=settings.EMAIL_HOST_USER,
                            recipient_list=valid_emails,
                            fail_silently=True
                        )
                        # Set cache so it doesn't spam emails every time someone searches
                        cache.set(cache_key, True, timeout=None)
                    
            if eligible_users >= 100:
                status = "Ready for Training (Awaiting Admin)"
            else:
                status = f"Learning ({eligible_users}/100 Players)"
        except Exception:
            status = "Learning (Database init pending)"

        return {
            "sim": 0.0,
            "status": status,
            "future_m1": 0.0, "future_m2": 0.0, "future_m3": 0.0,
            "future_m4": 0.0, "future_m5": 0.0, "future_m6": 0.0,
            "future_m7": 0.0, "future_m8": 0.0
        }

    default_resp = {
        "sim": 0.5,
        "future_m1": 0.0, "future_m2": 0.0, "future_m3": 0.0,
        "future_m4": 0.0, "future_m5": 0.0, "future_m6": 0.0,
        "future_m7": 0.0, "future_m8": 0.0
    }
    try:
        padded_norms = norms + [0.0] * (8 - len(norms))
        X_scaled = [min(float(n) / 10.0, 1.0) for n in padded_norms]
        
        X_input = np.array([X_scaled])
        future_preds = model.predict(X_input)[0]
        
        abs_m1 = min(X_scaled[0] + future_preds[0], 1.0) if len(future_preds) > 0 else X_scaled[0]
        abs_m2 = min(X_scaled[1] + future_preds[1], 1.0) if len(future_preds) > 1 else X_scaled[1]
        abs_m3 = min(X_scaled[2] + future_preds[2], 1.0) if len(future_preds) > 2 else X_scaled[2]
        
        weighted_score = float((abs_m1 * 0.5) + (abs_m2 * 0.3) + (abs_m3 * 0.2)) * 100
        
        return {
            "sim": round(max(weighted_score, 0.5), 1),
            "future_m1": float(future_preds[0]) * 10.0 if len(future_preds) > 0 else 0.0,
            "future_m2": float(future_preds[1]) * 10.0 if len(future_preds) > 1 else 0.0,
            "future_m3": float(future_preds[2]) * 10.0 if len(future_preds) > 2 else 0.0,
            "future_m4": float(future_preds[3]) * 10.0 if len(future_preds) > 3 else 0.0,
            "future_m5": float(future_preds[4]) * 10.0 if len(future_preds) > 4 else 0.0,
            "future_m6": float(future_preds[5]) * 10.0 if len(future_preds) > 5 else 0.0,
            "future_m7": float(future_preds[6]) * 10.0 if len(future_preds) > 6 else 0.0,
            "future_m8": float(future_preds[7]) * 10.0 if len(future_preds) > 7 else 0.0,
        }
    except Exception as e:
        print(f"Error in predict_performance: {e}")
        return default_resp