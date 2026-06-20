import os
import numpy as np
import joblib

_MODEL_CACHE = None

def get_model():
    global _MODEL_CACHE
    if _MODEL_CACHE is None:
        model_path = os.path.join(os.path.dirname(__file__), 'trained_rf_model.joblib')
        if os.path.exists(model_path):
            _MODEL_CACHE = joblib.load(model_path)
    return _MODEL_CACHE

def predict_performance(norms):
    default_resp = {
        "ai_score": 0.5,
        "future_m1": 0.0, "future_m2": 0.0, "future_m3": 0.0,
        "future_m4": 0.0, "future_m5": 0.0, "future_m6": 0.0,
        "future_m7": 0.0, "future_m8": 0.0
    }

    model = get_model()
    if not model:
        return default_resp
        
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
            "ai_score": round(max(weighted_score, 0.5), 1),
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