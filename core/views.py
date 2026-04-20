from django.shortcuts import render, redirect
from django.http import HttpResponseBadRequest
import os
import requests
import math
import numpy as np
from datetime import datetime
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .models import GameStat
from sklearn.metrics.pairwise import cosine_similarity

def fetch_fortnite_stats(username, platform):
    api_key = (os.getenv("FORTNITE_API_KEY") or "").strip()
    url = "https://fortnite-api.com/v2/stats/br/v2"
    account_type_map = {"pc": "epic", "epic": "epic", "xbl": "xbl", "psn": "psn"}
    account_type = account_type_map.get(platform, "epic")
    params = {"name": username, "accountType": account_type}
    headers = {"Authorization": api_key} if api_key else {}
    try:
        r = requests.get(url, params=params, headers=headers, timeout=10)
        if r.status_code != 200:
            return None, f"User Not Found ({r.status_code})"
        data = r.json()
        overall = data.get("data", {}).get("stats", {}).get("all", {}).get("overall", {})
        minutes = overall.get("minutesPlayed") or 0
        time_played = f"{round(minutes / 60)} Hours" if minutes else "Private"
        return {
            "main_stat": time_played,
            "detail_label": "Lifetime Wins",
            "detail_value": overall.get("wins", 0),
            "m1": float(overall.get("kd", 0)),
            "m2": float(overall.get("winRate", 0)),
            "m3": float(overall.get("wins", 0)),
            "raw_stats": [{"key": k, "value": v} for k, v in overall.items()]
        }, None
    except Exception as e:
        return None, str(e)

def fetch_clash_stats(username):
    api_key = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiIsImtpZCI6IjI4YTMxOGY3LTAwMDAtYTFlYi03ZmExLTJjNzQzM2M2Y2NhNSJ9.eyJpc3MiOiJzdXBlcmNlbGwiLCJhdWQiOiJzdXBlcmNlbGw6Z2FtZWFwaSIsImp0aSI6ImUyMzk4ZDliLTkwODktNDE2NS05MDgwLTkzZDRmODA3MjdlMSIsImlhdCI6MTc3NjU0Nzk5OCwic3ViIjoiZGV2ZWxvcGVyLzlhZjY2YjFkLWIzYmMtY2M1OS0xZDA5LTVkOTgwOWQxNzVmZiIsInNjb3BlcyI6WyJjbGFzaCJdLCJsaW1pdHMiOlt7InRpZXIiOiJkZXZlbG9wZXIvc2lsdmVyIiwidHlwZSI6InRocm90dGxpbmcifSx7ImNpZHJzIjpbIjE4OC4yOC40Ni4xMjYiXSwidHlwZSI6ImNsaWVudCJ9XX0.oatMV4Q3q38c893x4EIGoeAtK99IySMbHgQ-34Ph1ApzBdnrGV7oIlpggY12j46jLtDmt3yAJ-i5NEAcXEw-vg"
    clean_tag = username.replace("#", "").upper()
    url = f"https://api.clashofclans.com/v1/players/%23{clean_tag}"
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            return None, f"Clash Player Not Found ({r.status_code})"
        data = r.json()
        return {
            "main_stat": f"Town Hall {data.get('townHallLevel')}",
            "detail_label": "Trophies",
            "detail_value": data.get("trophies"),
            "m1": float(data.get("townHallLevel", 0)),
            "m2": float(data.get("trophies", 0)),
            "m3": float(data.get("warStars", 0)),
            "raw_stats": [
                {"key": "Best Trophies", "value": data.get("bestTrophies")},
                {"key": "War Stars", "value": data.get("warStars")},
                {"key": "Exp Level", "value": data.get("expLevel")},
                {"key": "Attack Wins", "value": data.get("attackWins")},
                {"key": "Defense Wins", "value": data.get("defenseWins")}
            ]
        }, None
    except Exception as e:
        return None, str(e)

def fetch_steam_stats(username):
    api_key = "D54C42B22786772ECE0A86D34FCDA4DA"
    steam_id = None
    if username.isdigit() and len(username) == 17:
        steam_id = username
    else:
        url_id = f"https://api.steampowered.com/ISteamUser/ResolveVanityURL/v1/?key={api_key}&vanityurl={username}"
        r_id = requests.get(url_id, timeout=10)
        steam_id = r_id.json().get("response", {}).get("steamid")
    if not steam_id:
        return None, "Steam User Not Found (Use Custom URL)"
    try:
        url_summary = f"https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/?key={api_key}&steamids={steam_id}"
        url_level = f"https://api.steampowered.com/IPlayerService/GetSteamLevel/v1/?key={api_key}&steamid={steam_id}"
        r_summary = requests.get(url_summary, timeout=10)
        r_level = requests.get(url_level, timeout=10)
        player = r_summary.json().get("response", {}).get("players", [{}])[0]
        level = r_level.json().get("response", {}).get("player_level", 0)
        state_map = {0: "Offline", 1: "Online", 2: "Busy", 3: "Away", 4: "Snooze"}
        created_ts = player.get("timecreated")
        created_date = datetime.fromtimestamp(created_ts).strftime('%d %b %Y') if created_ts else "Hidden"
        return {
            "main_stat": f"Steam Level {level}",
            "detail_label": "Status",
            "detail_value": state_map.get(player.get("personastate"), "Private"),
            "m1": float(level),
            "m2": float(player.get("personastate", 0)),
            "m3": float(player.get("timecreated", 0)) / 1000000,
            "raw_stats": [
                {"key": "Real Name", "value": player.get("realname", "N/A")},
                {"key": "Country", "value": player.get("loccountrycode", "N/A")},
                {"key": "Account Created", "value": created_date},
                {"key": "SteamID64", "value": steam_id}
            ]
        }, None
    except Exception as e:
        return None, str(e)

def fetch_hypixel_stats(username):
    api_key = "7587916d-ebcc-4d07-afc3-8869d9588202"
    url_uuid = f"https://api.mojang.com/users/profiles/minecraft/{username}"
    try:
        r_uuid = requests.get(url_uuid, timeout=10)
        if r_uuid.status_code != 200:
            return None, "Minecraft Account Not Found"
        uuid = r_uuid.json().get("id")
        url_stats = f"https://api.hypixel.net/v2/player?key={api_key}&uuid={uuid}"
        r_stats = requests.get(url_stats, timeout=10)
        data = r_stats.json()
        player = data.get("player")
        if not player:
            return None, "Player has no Hypixel data."
        exp = player.get("networkExp", 0)
        lvl = (math.sqrt(2 * exp + 15312.5) - 125) / 50
        login_ms = player.get("firstLogin", 0)
        login_date = datetime.fromtimestamp(login_ms / 1000.0).strftime('%d %b %Y') if login_ms else "Unknown"
        return {
            "main_stat": f"Network Level {max(1, math.floor(lvl))}",
            "detail_label": "Karma",
            "detail_value": f"{player.get('karma', 0):,}",
            "m1": float(lvl),
            "m2": float(player.get("karma", 0)) / 1000,
            "m3": float(player.get("achievementPoints", 0)),
            "raw_stats": [
                {"key": "Achievement Points", "value": player.get("achievementPoints", 0)},
                {"key": "First Joined", "value": login_date},
                {"key": "Recent Game", "value": player.get("mostRecentGameType", "None")}
            ]
        }, None
    except Exception as e:
        return None, str(e)

def game_search(request):
    game_choice = request.GET.get("game_choice")
    username = (request.GET.get("username") or "").strip()
    platform = (request.GET.get("platform") or "").strip()
    if not username or not game_choice:
        return HttpResponseBadRequest("Missing required fields")
    recent_searches = request.session.get('recent_searches', [])
    if username and username not in recent_searches:
        recent_searches.insert(0, username)
        request.session['recent_searches'] = recent_searches[:5]
    stats_data = None
    error = None
    if game_choice == "fortnite":
        stats_data, error = fetch_fortnite_stats(username, platform)
    elif game_choice == "clash":
        stats_data, error = fetch_clash_stats(username)
    elif game_choice == "steam":
        stats_data, error = fetch_steam_stats(username)
    elif game_choice == "hypixel":
        stats_data, error = fetch_hypixel_stats(username)
    else:
        error = "Game not supported yet."
    return render(request, "core/results.html", {
        "username": username,
        "game_choice": game_choice,
        "platform": platform,
        "stats": stats_data,
        "error": error
    })

def home(request):
    history = request.session.get('recent_searches', [])
    return render(request, "core/home.html", {'history': history})

def clear_history(request):
    if 'recent_searches' in request.session:
        del request.session['recent_searches']
    return redirect('home')

def login_view(request):
    if request.method == "POST":
        u = request.POST.get('username')
        p = request.POST.get('password')
        user = authenticate(username=u, password=p)
        if user is not None:
            login(request, user)
            return redirect('dashboard')
    return render(request, 'core/login.html')

def signup_view(request):
    if request.method == "POST":
        u = request.POST.get('username')
        p = request.POST.get('password')
        User.objects.create_user(username=u, password=p)
        return redirect('home')
    return render(request, 'core/signup.html')

def logout_view(request):
    logout(request)
    return redirect('login')

@login_required(login_url='login')
def dashboard(request):
    user_stats = GameStat.objects.filter(user=request.user)
    all_other_stats = GameStat.objects.exclude(user=request.user)
    recommendations = []
    
    if user_stats.exists():
        my_stat = user_stats.first()
        my_vector = np.array([my_stat.metric_1, my_stat.metric_2, (my_stat.metric_3 / 100)]).reshape(1, -1)
        
        for other in all_other_stats:
            other_vector = np.array([other.metric_1, other.metric_2, (other.metric_3 / 100)]).reshape(1, -1)
            
            sim_score = cosine_similarity(my_vector, other_vector)[0][0]
            
            
            dynamic_score = sim_score * 100
            if dynamic_score > 99 and (my_stat.metric_1 != other.metric_1):
                dynamic_score -= (abs(my_stat.metric_1 - other.metric_1) * 10)

            recommendations.append({
                'username': other.user.username,
                'game_name': other.game_username,
                'score': round(max(min(dynamic_score, 100), 0), 1),
                'platform': other.platform
            })
    
    recommendations = sorted(recommendations, key=lambda x: x['score'], reverse=True)[:5]
    return render(request, 'core/dashboard.html', {'saved_games': user_stats, 'matches': recommendations})

@login_required
def link_account(request):
    if request.method == "POST":
        game_u = request.POST.get('game_username')
        game_c = request.POST.get('game_choice')
        stat = request.POST.get('main_stat')
        m1 = request.POST.get('m1', 0)
        m2 = request.POST.get('m2', 0)
        m3 = request.POST.get('m3', 0)
        GameStat.objects.update_or_create(
            user=request.user,
            game_username=game_u,
            defaults={
                'platform': game_c,
                'time_played': stat,
                'metric_1': float(m1),
                'metric_2': float(m2),
                'metric_3': float(m3)
            }
        )
        return redirect('dashboard')
@login_required
def delete_account(request, stat_id):
    stat = GameStat.objects.get(id=stat_id, user=request.user)
    stat.delete()
    return redirect('dashboard')