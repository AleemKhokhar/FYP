from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.core.cache import cache
from django.template.loader import get_template
from django.conf import settings
from django.contrib import messages

from allauth.account.models import EmailAddress
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

import os
import requests
import math
import re
import numpy as np
import json
from datetime import datetime
from io import BytesIO
from xhtml2pdf import pisa
from sklearn.metrics.pairwise import cosine_similarity

from .models import SavedGame, Profile
from .forms import ProfileUpdateForm, AccountUpdateForm
from .ai_model import predict_performance
from .models import APILog
import time
from .integrations import GAME_REGISTRY

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

@login_required
def account_settings(request):
    if request.method == 'POST':
        form = AccountUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Your account details have been updated successfully.")
            return redirect('dashboard')
    else:
        form = AccountUpdateForm(instance=request.user)
    return render(request, 'core/account_settings.html', {'form': form})

@login_required
def delete_user_profile(request):
    if request.method == 'POST':
        user_to_delete = request.user
        logout(request)
        user_to_delete.delete()
        messages.success(request, "Account erased.")
        return redirect('home')
    return redirect('dashboard')

@login_required
def export_user_data(request):
    user_games = SavedGame.objects.filter(user=request.user)
    export_data = {
        "account_info": {
            "username": request.user.username,
            "email": request.user.email,
            "date_joined": request.user.date_joined.isoformat()
        },
        "telemetry_data": []
    }
    for game in user_games:
        export_data["telemetry_data"].append({
            "platform": game.platform,
            "game_username": game.game_username,
            "time_played": game.time_played,
            "ai_score": game.ai_score,
            "raw_metrics": {"m1": game.m1, "m2": game.m2, "m3": game.m3},
            "date_saved": game.date_saved.isoformat() if game.date_saved else None
        })
    response = JsonResponse(export_data, json_dumps_params={'indent': 4})
    response['Content-Disposition'] = f'attachment; filename="{request.user.username}_export.json"'
    return response

def home(request):
    history = request.session.get('recent_searches', [])
    return render(request, "core/home.html", {'history': history})

def game_search(request):
    game_choice = request.GET.get("game_choice")
    username = (request.GET.get("username") or "").strip()
    platform = (request.GET.get("platform") or "").strip()
    
    if not username or not game_choice:
        return HttpResponseBadRequest("Missing fields")
        
    integration = GAME_REGISTRY.get(game_choice)
    if not integration:
        return HttpResponseBadRequest("Unsupported game")

    recent_searches = request.session.get('recent_searches', [])
    if username and username not in recent_searches:
        recent_searches.insert(0, username)
        request.session['recent_searches'] = recent_searches[:5]
        
    cache_key = f"stats_{game_choice}_{username}_{platform}"
    stats_data = cache.get(cache_key)
    error = None
    
    if not stats_data:

        start_time = time.time()

        status_code = 200

        stats_data, error = integration.fetch_stats(username, platform)

        elapsed_time = time.time() - start_time

        if error:

            status_code = 400



        APILog.objects.create(

            endpoint=f"Search Engine: {game_choice}",

            status_code=status_code,

            response_time=round(elapsed_time, 2)

        )

            

        if stats_data and not error:

            cache.set(cache_key, stats_data, 300)
            
    is_linked = False
    
    if stats_data and not error:
        m1_val = float(stats_data.get('m1', 0))
        m2_val = float(stats_data.get('m2', 0))
        m3_val = float(stats_data.get('m3', 0))
        
        norm_m1, norm_m2, norm_m3, insights = integration.get_insights(m1_val, m2_val, m3_val)

        prediction = predict_performance(norm_m1, norm_m2, norm_m3)
        stats_data['ai_score'] = prediction
        stats_data['insights'] = insights

        if request.user.is_authenticated:
            is_linked = SavedGame.objects.filter(user=request.user, game_username=username, platform=game_choice).exists()
            
        if 'raw_stats' in stats_data:
            live_data = {s['key']: s['value'] for s in stats_data['raw_stats']}
            live_data['ai_score'] = prediction
            broadcast_stats(username, live_data)
            
    return render(request, "core/results.html", {
        "username": username, "game_choice": game_choice, "platform": platform,
        "stats": stats_data, "error": error, "is_linked": is_linked
    })

@login_required
def link_account(request):
    if request.method == "POST":
        game_u, game_c = request.POST.get('game_username'), request.POST.get('game_choice')
        stat, ai_s = request.POST.get('main_stat'), request.POST.get('ai_score', 0)
        m1, m2, m3 = request.POST.get('m1', 0), request.POST.get('m2', 0), request.POST.get('m3', 0)
        SavedGame.objects.update_or_create(
            user=request.user, game_username=game_u, platform=game_c,
            defaults={'time_played': stat, 'm1': m1, 'm2': m2, 'm3': m3, 'ai_score': float(ai_s or 0)}
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
                'username': other.user.username, 'game_name': other.game_username,
                'score': round(sim * 100, 1), 'platform': other.platform
            })
    recommendations = sorted(recommendations, key=lambda x: x['score'], reverse=True)[:5]
    return render(request, 'core/dashboard.html', {
        'saved_games': user_games, 'matches': recommendations,
        'chart_labels': chart_labels, 'chart_data': chart_data
    })

def leaderboard(request):
    top_scores = SavedGame.objects.order_by('-ai_score')[:10]
    return render(request, 'core/leaderboard.html', {'top_scores': top_scores})

@login_required
def download_report(request, stat_id):
    stat = get_object_or_404(SavedGame, id=stat_id, user=request.user)
    template = get_template('core/pdf_template.html')
    html = template.render({'stat': stat, 'user': request.user})
    
    result = BytesIO()
    pdf = pisa.CreatePDF(BytesIO(html.encode("UTF-8")), dest=result)
    
    if pdf.err:
        return HttpResponseBadRequest("Error generating PDF")
        
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
    game, platform = request.GET.get('game_choice'), request.GET.get('platform', 'epic')
    d1, d2, error = None, None, None
    integration = GAME_REGISTRY.get(game)
    if u1 and u2 and integration:
        d1, _ = integration.fetch_stats(u1, platform)
        d2, _ = integration.fetch_stats(u2, platform)
        if d1 and d2:
            n1_m1, n1_m2, n1_m3, _ = integration.get_insights(d1['m1'], d1['m2'], d1['m3'])
            n2_m1, n2_m2, n2_m3, _ = integration.get_insights(d2['m1'], d2['m2'], d2['m3'])
            d1['ai_score'] = predict_performance(n1_m1, n1_m2, n1_m3)
            d2['ai_score'] = predict_performance(n2_m1, n2_m2, n2_m3)
        else:
            error = "Players not found."
    return render(request, 'core/comparison.html', {'user1': u1, 'user2': u2, 'data1': d1, 'data2': d2, 'game_choice': game, 'error': error})

def clear_history(request):
    if 'recent_searches' in request.session: del request.session['recent_searches']
    return redirect('home')

def login_view(request):
    error = None
    if request.method == "POST":
        u, p = request.POST.get('username'), request.POST.get('password')
        user = authenticate(request, username=u, password=p)
        if user:
            if EmailAddress.objects.filter(user=user, verified=True).exists():
                login(request, user); return redirect('dashboard')
            else: error = "Verify email first."
        else: error = "Invalid login."
    return render(request, 'core/login.html', {'error': error})

def signup_view(request):
    error = None
    if request.method == "POST":
        u, e, p = request.POST.get('username'), request.POST.get('email'), request.POST.get('password')
        if User.objects.filter(username=u).exists(): error = "Username taken."
        elif User.objects.filter(email=e).exists(): error = "Email registered."
        else:
            user = User.objects.create_user(username=u, email=e, password=p)
            email_address = EmailAddress.objects.create(user=user, email=e, primary=True, verified=False)
            email_address.send_confirmation(request)
            return redirect('login')
    return render(request, 'core/signup.html', {'error': error})

def logout_view(request):
    logout(request)
    return redirect('login')
