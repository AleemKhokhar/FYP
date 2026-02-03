from django.shortcuts import render
from django.http import HttpResponseBadRequest
import os
import requests

def home(request):
    history = request.session.get('recent_searches', [])
    return render(request, "core/home.html", {'history': history})

def game_search(request):
    username = (request.GET.get("q") or "").strip()
    platform = (request.GET.get("platform") or "").strip()

    if not username or not platform:
        return HttpResponseBadRequest("Missing username or platform")

    recent_searches = request.session.get('recent_searches', [])
    if username and username not in recent_searches:
        recent_searches.insert(0, username)
        request.session['recent_searches'] = recent_searches[:5]

    account_type_map = {"pc": "epic", "epic": "epic", "xbl": "xbl", "psn": "psn"}
    account_type = account_type_map.get(platform)
    if not account_type:
        return HttpResponseBadRequest("Invalid platform")

    api_key = (os.getenv("FORTNITE_API_KEY") or "").strip()
    
    url = "https://fortnite-api.com/v2/stats/br/v2"
    params = {"name": username, "accountType": account_type}
    headers = {"Authorization": api_key} if api_key else {}

    try:
        r = requests.get(url, params=params, headers=headers, timeout=10)
        content_type = r.headers.get("Content-Type", "")
        data = r.json() if "application/json" in content_type else {}

        if r.status_code != 200:
            return render(request, "core/results.html", {
                "username": username,
                "platform": platform,
                "time_played": "Not Found",
                "all_stats": [],
                "error": f"API Error {r.status_code}: {data.get('error') or r.text}"
            })

        overall = data.get("data", {}).get("stats", {}).get("all", {}).get("overall", {})

        if not isinstance(overall, dict) or not overall:
            time_played = "Not Found (private profile or no data)"
            all_stats = []
        else:
            minutes = overall.get("minutesPlayed") or 0
            time_played = f"{round(minutes / 60)} Hours" if minutes else "Not Available"
            all_stats = [{"key": k, "value": v} for k, v in overall.items()]

        return render(request, "core/results.html", {
            "username": username,
            "platform": platform,
            "time_played": time_played,
            "all_stats": all_stats
        })

    except requests.exceptions.RequestException as e:
        return render(request, "core/results.html", {
            "username": username,
            "platform": platform,
            "time_played": "Not Found",
            "all_stats": [],
            "error": f"Network error: {e}"
        })
from django.shortcuts import redirect

def clear_history(request):
    if 'recent_searches' in request.session:
        del request.session['recent_searches']
    return redirect('home')