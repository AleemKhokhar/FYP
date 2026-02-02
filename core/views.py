from django.shortcuts import render
from django.http import HttpResponseBadRequest
import os
import requests

def home(request):
    return render(request, "core/home.html")

def game_search(request):
    username = (request.GET.get("q") or "").strip()
    platform = (request.GET.get("platform") or "").strip()

    if not username or not platform:
        return HttpResponseBadRequest("Missing username or platform")

    account_type_map = {"pc": "epic", "xbl": "xbl", "psn": "psn"}
    account_type = account_type_map.get(platform)
    if not account_type:
        return HttpResponseBadRequest("Invalid platform")

    api_key = (os.getenv("FORTNITE_API_KEY") or "").strip()
    if not api_key:
        return render(request, "core/results.html", {
            "username": username,
            "platform": platform,
            "time_played": "Not Found",
            "all_stats": [],
            "error": "Server is missing FORTNITE_API_KEY (check your .env/settings)."
        })

    url = "https://fortnite-api.com/v2/stats/br/v2"
    params = {"name": username, "accountType": account_type}
    headers = {"Authorization": api_key}  # if needed: f"Bearer {api_key}"

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

        overall = (
            data.get("data", {})
                .get("stats", {})
                .get("all", {})
                .get("overall", {})
        )

        if not isinstance(overall, dict) or not overall:
            time_played = "Not Found (private profile or no data)"
            all_stats = []
        else:
            time_played = overall.get("minutesPlayed") or overall.get("timePlayed") or "Not Available"
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
