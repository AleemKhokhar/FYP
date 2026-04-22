from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpResponseBadRequest
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.core.cache import cache
from django.template.loader import get_template
from django.conf import settings
from allauth.account.models import EmailAddress

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

import os
import requests
import math
import re
import numpy as np
from datetime import datetime
from io import BytesIO
from xhtml2pdf import pisa
from sklearn.metrics.pairwise import cosine_similarity

from .models import SavedGame, Profile
from .forms import ProfileUpdateForm
from .ai_model import predict_performance
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from allauth.account.models import EmailAddress



def broadcast_stats(username, data):
    channel_layer = get_channel_layer()
    safe_name = re.sub(r'[^a-zA-Z0-9._-]', '_', username)
    async_to_sync(channel_layer.group_send)(
        f"stats_{safe_name}",
        {
            "type": "stats_update",
            "stats": data,
        },
    )

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
    api_key = os.getenv("CLASH_API_KEY")
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
    api_key = os.getenv("STEAM_API_KEY")
    steam_id = None
    if username.isdigit() and len(username) == 17:
        steam_id = username
    else:
        url_id = f"https://api.steampowered.com/ISteamUser/ResolveVanityURL/v1/?key={api_key}&vanityurl={username}"
        r_id = requests.get(url_id, timeout=10)
        steam_id = r_id.json().get("response", {}).get("steamid")
    if not steam_id:
        return None, "Steam User Not Found"
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
    api_key = os.getenv("HYPIXEL_API_KEY")
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
            "m2": float(player.get('karma', 0)) / 1000,
            "m3": float(player.get("achievementPoints", 0)),
            "raw_stats": [
                {"key": "Achievement Points", "value": player.get("achievementPoints", 0)},
                {"key": "First Joined", "value": login_date},
                {"key": "Recent Game", "value": player.get("mostRecentGameType", "None")}
            ]
        }, None
    except Exception as e:
        return None, str(e)

def home(request):
    history = request.session.get('recent_searches', [])
    return render(request, "core/home.html", {'history': history})

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
    
    cache_key = f"stats_{game_choice}_{username}_{platform}"
    stats_data = cache.get(cache_key)
    error = None

    if not stats_data:
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
        
        if stats_data and not error:
            cache.set(cache_key, stats_data, 300)

    is_linked = False
    if stats_data and not error:
        prediction = predict_performance(
            stats_data.get('m1', 0),
            stats_data.get('m2', 0),
            stats_data.get('m3', 0)
        )
        stats_data['ai_score'] = prediction

        if request.user.is_authenticated:
            is_linked = SavedGame.objects.filter(
                user=request.user, 
                game_username=username, 
                platform=game_choice
            ).exists()

        insights = []
        m1_val = float(stats_data.get('m1', 0))
        if game_choice == 'fortnite':
            if m1_val > 2.5: insights.append("Combat: K/D ratio suggests high mechanical skill.")
            else: insights.append("Combat: Improve positioning to increase K/D.")
        elif game_choice == 'clash':
            if m1_val >= 12: insights.append("Progression: High Town Hall level detected.")
        
        stats_data['insights'] = insights

        if 'raw_stats' in stats_data:
            live_data = {s['key']: s['value'] for s in stats_data['raw_stats']}
            live_data['ai_score'] = prediction
            broadcast_stats(username, live_data)

    return render(request, "core/results.html", {
        "username": username,
        "game_choice": game_choice,
        "platform": platform,
        "stats": stats_data,
        "error": error,
        "is_linked": is_linked
    })

@login_required
def link_account(request):
    if request.method == "POST":
        game_u = request.POST.get('game_username')
        game_c = request.POST.get('game_choice')
        stat = request.POST.get('main_stat')
        m1 = request.POST.get('m1', 0)
        m2 = request.POST.get('m2', 0)
        m3 = request.POST.get('m3', 0)
        ai_s = request.POST.get('ai_score', 0)
        
        SavedGame.objects.update_or_create(
            user=request.user,
            game_username=game_u,
            platform=game_c,
            defaults={
                'time_played': stat,
                'm1': m1,
                'm2': m2,
                'm3': m3,
                'ai_score': float(ai_s or 0)
            }
        )
        return redirect('dashboard')

@login_required
def dashboard(request):
    user_games = SavedGame.objects.filter(user=request.user).order_by('date_saved')
    all_other_games = SavedGame.objects.exclude(user=request.user)
    
    chart_labels = [s.date_saved.strftime("%d %b") for s in user_games]
    chart_data = [s.ai_score for s in user_games]
    
    recommendations = []
    if user_games.exists():
        my_game = user_games.last()
        my_vec = np.array([float(my_game.m1 or 0), float(my_game.m2 or 0), (float(my_game.m3 or 0) / 100)]).reshape(1, -1)
        
        for other in all_other_games:
            other_vec = np.array([float(other.m1 or 0), float(other.m2 or 0), (float(other.m3 or 0) / 100)]).reshape(1, -1)
            sim = cosine_similarity(my_vec, other_vec)[0][0]
            recommendations.append({
                'username': other.user.username,
                'game_name': other.game_username,
                'score': round(sim * 100, 1),
                'platform': other.platform
            })
    
    recommendations = sorted(recommendations, key=lambda x: x['score'], reverse=True)[:5]
    
    return render(request, 'core/dashboard.html', {
        'saved_games': user_games, 
        'matches': recommendations,
        'chart_labels': chart_labels,
        'chart_data': chart_data
    })

def leaderboard(request):
    top_scores = SavedGame.objects.order_by('-ai_score')[:10]
    return render(request, 'core/leaderboard.html', {'top_scores': top_scores})

@login_required
def download_report(request, stat_id):
    stat = get_object_or_404(SavedGame, id=stat_id, user=request.user)
    template = get_template('core/pdf_template.html')
    context = {'stat': stat}
    html = template.render(context)
    result = BytesIO()
    pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
    response = HttpResponse(result.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{stat.game_username}_report.pdf"'
    return response

@login_required
def delete_account(request, stat_id):
    stat = get_object_or_404(SavedGame, id=stat_id, user=request.user)
    stat.delete()
    return redirect('dashboard')

@login_required
def profile_edit(request):
    profile, created = Profile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        p_form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)
        if p_form.is_valid():
            p_form.save()
            return redirect('dashboard')
    else:
        p_form = ProfileUpdateForm(instance=profile)
    return render(request, 'core/profile_edit.html', {'p_form': p_form})

def player_compare(request):
    u1, u2 = request.GET.get('user1', '').strip(), request.GET.get('user2', '').strip()
    game = request.GET.get('game_choice')
    platform = request.GET.get('platform', 'epic')
    d1, d2, error = None, None, None

    if u1 and u2 and game:
        if game == "fortnite":
            d1, _ = fetch_fortnite_stats(u1, platform)
            d2, _ = fetch_fortnite_stats(u2, platform)
        elif game == "clash":
            d1, _ = fetch_clash_stats(u1)
            d2, _ = fetch_clash_stats(u2)
        elif game == "steam":
            d1, _ = fetch_steam_stats(u1)
            d2, _ = fetch_steam_stats(u2)
        elif game == "hypixel":
            d1, _ = fetch_hypixel_stats(u1)
            d2, _ = fetch_hypixel_stats(u2)

        if d1 and d2:
            d1['ai_score'] = predict_performance(d1['m1'], d1['m2'], d1['m3'])
            d2['ai_score'] = predict_performance(d2['m1'], d2['m2'], d2['m3'])
        else:
            error = "One or both players could not be found."

    return render(request, 'core/comparison.html', {'user1': u1, 'user2': u2, 'data1': d1, 'data2': d2, 'game_choice': game, 'error': error})

def clear_history(request):
    if 'recent_searches' in request.session: del request.session['recent_searches']
    return redirect('home')

def login_view(request):
    error = None
    if request.method == "POST":
        u = request.POST.get('username')
        p = request.POST.get('password')
        user = authenticate(request, username=u, password=p)
        
        if user is not None:
            if EmailAddress.objects.filter(user=user, verified=True).exists():
                login(request, user)
                return redirect('dashboard')
            else:
                error = "You must verify your email before logging in."
        else:
            error = "Invalid username or password."
            
    return render(request, 'core/login.html', {'error': error})

def signup_view(request):
    error = None
    if request.method == "POST":
        u = request.POST.get('username')
        e = request.POST.get('email')
        p = request.POST.get('password')
        
        if User.objects.filter(username=u).exists():
            error = "Username is already taken. Please choose another."
        elif User.objects.filter(email=e).exists():
            error = "Email is already registered."
        else:
            user = User.objects.create_user(username=u, email=e, password=p)
            
            email_address = EmailAddress.objects.create(user=user, email=e, primary=True, verified=False)
            email_address.send_confirmation(request)
            
            return redirect('login')
            
    return render(request, 'core/signup.html', {'error': error})

def logout_view(request):
    logout(request)
    return redirect('login')