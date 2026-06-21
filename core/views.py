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
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from allauth.account.models import EmailAddress
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

import os
import re
import time
import json
import math
from datetime import datetime
from io import BytesIO

import requests
import numpy as np
from xhtml2pdf import pisa
import concurrent.futures

from .models import SavedGame, Profile, APILog, CrowdsourcedStatSnapshot
from .forms import ProfileUpdateForm, AccountUpdateForm
from .ai_model import predict_performance
from .integrations import GAME_REGISTRY, get_euclidean_similarity

def broadcast_stats(username, data):
    channel_layer = get_channel_layer()
    safe_name = re.sub(r'[^a-zA-Z0-9._-]', '_', username)
    try:
        async_to_sync(channel_layer.group_send)(
            f"stats_{safe_name}",
            {
                "type": "stats_update",
                "stats": data,
            },
        )
    except Exception as e:
        print(f"WebSocket Broadcast Error for {username}: {e}")

@login_required
def account_settings(request):
    if request.method == 'POST':
        old_email = User.objects.get(pk=request.user.pk).email
        form = AccountUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            new_email = form.cleaned_data.get('email')
            if new_email != old_email:
                EmailAddress.objects.filter(user=request.user).delete()                
                user = form.save(commit=False)
                user.email = new_email
                user.save()                
                email_address = EmailAddress.objects.create(
                    user=user, 
                    email=new_email, 
                    primary=True, 
                    verified=False
                )
                email_address.send_confirmation(request)                
                logout(request)                
                messages.success(request, "Your email has been updated successfully. A verification link has been sent to your new email. Please verify it before logging in again.")
                return redirect('login')
            else:
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
    if username:
        search_entry = {'username': username, 'game_choice': game_choice, 'platform': platform}
        recent_searches = [s for s in recent_searches if isinstance(s, dict) and s != search_entry]
        recent_searches.insert(0, search_entry)
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
            try:
                from datetime import date
                CrowdsourcedStatSnapshot.objects.get_or_create(
                    game_choice=game_choice,
                    username=username,
                    date=date.today(),
                    defaults={
                        'platform': platform,
                        'm1': float(stats_data.get('m1', 0)),
                        'm2': float(stats_data.get('m2', 0)),
                        'm3': float(stats_data.get('m3', 0)),
                        'm4': float(stats_data.get('m4', 0)),
                        'm5': float(stats_data.get('m5', 0)),
                        'm6': float(stats_data.get('m6', 0)),
                        'm7': float(stats_data.get('m7', 0)),
                        'm8': float(stats_data.get('m8', 0)),
                    }
                )
            except Exception as e:
                pass
            
    is_linked = False
    
    if stats_data and not error:
        
        insights_data = integration.get_insights(stats_data)

        prediction = predict_performance(insights_data['norms'], game_choice)
        comp_vec = integration.get_comparison_vector(stats_data)
        stats_data['ai_score'] = round((sum(comp_vec) / len(comp_vec)) * 100, 1) if comp_vec else 0.0
        stats_data['insights'] = insights_data['insights']
        stats_data['future_predictions'] = integration.get_future_predictions(prediction, stats_data)
        if prediction.get('status'):
            stats_data['future_predictions'] = [{"label": "AI Status", "value": prediction['status']}]

        if request.user.is_authenticated:
            is_linked = SavedGame.objects.filter(user=request.user, game_username=username, platform=game_choice).exists()
            
        if 'raw_stats' in stats_data:
            live_data = {s['key']: s['value'] for s in stats_data['raw_stats']}
            live_data['ai_score'] = stats_data['ai_score']
            live_data['main_stat'] = stats_data.get('main_stat')
            live_data['detail_value'] = stats_data.get('detail_value')
            broadcast_stats(username, live_data)
            
    return render(request, "core/results.html", {
        "username": username, "game_choice": game_choice, "platform": platform,
        "stats": stats_data, "error": error, "is_linked": is_linked
    })

def api_refresh(request):
    game_choice = request.GET.get("game_choice")
    username = request.GET.get("username", "").strip()
    platform = request.GET.get("platform", "").strip()

    integration = GAME_REGISTRY.get(game_choice)
    if not integration or not username:
        return JsonResponse({"error": "Invalid request"}, status=400)
        
    cache_key = f"stats_{game_choice}_{username}_{platform}"
    refresh_lock_key = f"lock_{cache_key}"
    if cache.get(refresh_lock_key):
        return JsonResponse({"status": "throttled"})

    stats_data, error = integration.fetch_stats(username, platform)
    if error:
        return JsonResponse({"error": error}, status=400)

    try:
        from datetime import date
        CrowdsourcedStatSnapshot.objects.get_or_create(
            game_choice=game_choice,
            username=username,
            date=date.today(),
            defaults={
                'platform': platform,
                'm1': float(stats_data.get('m1', 0)),
                'm2': float(stats_data.get('m2', 0)),
                'm3': float(stats_data.get('m3', 0)),
                'm4': float(stats_data.get('m4', 0)),
                'm5': float(stats_data.get('m5', 0)),
                'm6': float(stats_data.get('m6', 0)),
                'm7': float(stats_data.get('m7', 0)),
                'm8': float(stats_data.get('m8', 0)),
            }
        )
    except Exception as e:
        pass

    insights_data = integration.get_insights(stats_data)
    prediction = predict_performance(insights_data['norms'], game_choice)
    comp_vec = integration.get_comparison_vector(stats_data)
    stats_data['ai_score'] = round((sum(comp_vec) / len(comp_vec)) * 100, 1) if comp_vec else 0.0
    stats_data['future_predictions'] = integration.get_future_predictions(prediction, stats_data)
    if prediction.get('status'):
        stats_data['future_predictions'] = [{"label": "AI Status", "value": prediction['status']}]

    cache.set(cache_key, stats_data, 300)
    cache.set(refresh_lock_key, True, 60)

    if 'raw_stats' in stats_data:
        live_data = {s['key']: s['value'] for s in stats_data['raw_stats']}
        live_data['ai_score'] = stats_data['ai_score']
        live_data['main_stat'] = stats_data.get('main_stat')
        live_data['detail_value'] = stats_data.get('detail_value')
        broadcast_stats(username, live_data)

    return JsonResponse({"status": "refreshed"})

@login_required
def link_account(request):
    if request.method == "POST":
        if SavedGame.objects.filter(user=request.user).count() >= 12:
            messages.error(request, "You can only link up to 12 accounts.")
            return redirect('dashboard')
        game_u = request.POST.get('game_username')
        game_c = request.POST.get('game_choice')
        stat = request.POST.get('main_stat')
        ai_s = request.POST.get('ai_score', 0)
        m1 = request.POST.get('m1', 0)
        m2 = request.POST.get('m2', 0)
        m3 = request.POST.get('m3', 0)
        SavedGame.objects.update_or_create(
            user=request.user, 
            game_username=game_u, 
            platform=game_c,
            defaults={
                'time_played': stat, 'm1': m1, 'm2': m2, 'm3': m3, 'ai_score': float(ai_s or 0)
            }
        )
    return redirect('dashboard')

@login_required
def dashboard(request):
    user_games = SavedGame.objects.filter(user=request.user).order_by('date_saved')
    all_other_games = SavedGame.objects.exclude(user=request.user).select_related('user').order_by('-date_saved')[:100]
    
    charts_config = {}
    
    if user_games.exists():
        for game in user_games:
            integration = GAME_REGISTRY.get(game.platform)
            if not integration: continue
            
            history = CrowdsourcedStatSnapshot.objects.filter(game_choice=game.platform, username=game.game_username).order_by('date')
            if not history.exists(): continue
            
            empty_stats = {"m1": 0, "m2": 0, "m3": 0, "m4": 0, "m5": 0, "m6": 0, "m7": 0, "m8": 0}
            display_info = integration.get_comparison_display(empty_stats)
            stat_names = [item["key"] for item in display_info]
            
            labels = []
            datasets = {name: [] for name in stat_names}
            pred_datasets = {name: [] for name in stat_names}
            
            for h in history:
                labels.append(h.date.strftime("%d %b"))
                h_stats = {'m1': h.m1, 'm2': h.m2, 'm3': h.m3, 'm4': h.m4, 'm5': h.m5, 'm6': h.m6, 'm7': h.m7, 'm8': h.m8}
                try:
                    vec = integration.get_comparison_vector(h_stats)
                    for i, name in enumerate(stat_names):
                        if i < len(vec):
                            val = vec[i] * 100
                            datasets[name].append(val)
                            pred_datasets[name].append(None)
                except Exception as e:
                    pass
                    
            last_snap = history.last()
            stats_data = {'m1': last_snap.m1, 'm2': last_snap.m2, 'm3': last_snap.m3, 'm4': last_snap.m4, 'm5': last_snap.m5, 'm6': last_snap.m6, 'm7': last_snap.m7, 'm8': last_snap.m8}
            try:
                insights_data = integration.get_insights(stats_data)
                prediction = predict_performance(insights_data['norms'], game.platform)
                
                if not prediction.get('status'):
                    from datetime import timedelta
                    labels.append((last_snap.date + timedelta(days=7)).strftime("%d %b (Pred)"))
                    
                    futures = integration.calculate_future(stats_data, prediction, integration.MAX_VALS)
                    future_stats_data = {f"m{i+1}": f for i, f in enumerate(futures)}
                    future_vec = integration.get_comparison_vector(future_stats_data)
                    
                    for i, name in enumerate(stat_names):
                        if i < len(future_vec):
                            datasets[name].append(None)
                            
                            pred_datasets[name][-1] = datasets[name][-2] if len(datasets[name]) > 1 else datasets[name][-1]
                            
                            future_val = future_vec[i] * 100
                            pred_datasets[name].append(future_val)
            except Exception as e:
                pass
                
            charts_config[game.id] = {
                'labels': labels,
                'datasets': datasets,
                'pred_datasets': pred_datasets
            }

    recommendations = []
    if user_games.exists():
        my_game = user_games.last()
        my_integration = GAME_REGISTRY.get(my_game.platform)
        if my_integration:
            my_vec = my_integration.get_comparison_vector({
                "m1": my_game.m1 or 0, "m2": my_game.m2 or 0, "m3": my_game.m3 or 0
            })
            for other in all_other_games:
                other_integration = GAME_REGISTRY.get(other.platform)
                if other_integration:
                    other_vec = other_integration.get_comparison_vector({
                        "m1": other.m1 or 0, "m2": other.m2 or 0, "m3": other.m3 or 0
                    })
                    sim = get_euclidean_similarity(my_vec, other_vec)
                    recommendations.append({
                        'username': other.user.username, 'game_name': other.game_username,
                        'score': sim, 'platform': other.platform
                    })
    recommendations = sorted(recommendations, key=lambda x: x['score'], reverse=True)[:5]
    return render(request, 'core/dashboard.html', {
        'saved_games': user_games, 'matches': recommendations,
        'charts_config': json.dumps(charts_config)
    })

def leaderboard(request):
    top_scores = SavedGame.objects.select_related('user').order_by('-ai_score')[:10]
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
    u1 = request.GET.get('user1', '').strip()
    u2 = request.GET.get('user2', '').strip()
    game = request.GET.get('game_choice')
    platform = request.GET.get('platform', 'epic')
    d1, d2, error = None, None, None
    similarity = None
    integration = GAME_REGISTRY.get(game)
    if u1 and u2 and integration:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future1 = executor.submit(integration.fetch_stats, u1, platform)
            future2 = executor.submit(integration.fetch_stats, u2, platform)
            d1, _ = future1.result()
            d2, _ = future2.result()
        if d1 and d2:
            i1 = integration.get_insights(d1)
            i2 = integration.get_insights(d2)
            p1 = predict_performance(i1['norms'], game)
            p2 = predict_performance(i2['norms'], game)
            v1 = integration.get_comparison_vector(d1)
            v2 = integration.get_comparison_vector(d2)
            d1['ai_score'] = round((sum(v1) / len(v1)) * 100, 1) if v1 else 0.0
            d2['ai_score'] = round((sum(v2) / len(v2)) * 100, 1) if v2 else 0.0
            d1['future_predictions'] = integration.get_future_predictions(p1, d1)
            d2['future_predictions'] = integration.get_future_predictions(p2, d2)
            if p1.get('status'):
                d1['future_predictions'] = [{"label": "AI Status", "value": p1['status']}]
            if p2.get('status'):
                d2['future_predictions'] = [{"label": "AI Status", "value": p2['status']}]
            similarity = get_euclidean_similarity(v1, v2)
            d1['raw_stats'] = integration.get_comparison_display(d1)
            d2['raw_stats'] = integration.get_comparison_display(d2)
        else:
            error = "Players not found."
    return render(request, 'core/comparison.html', {'user1': u1, 'user2': u2, 'data1': d1, 'data2': d2, 'game_choice': game, 'error': error, 'similarity': similarity})

def clear_history(request):
    if 'recent_searches' in request.session: 
        del request.session['recent_searches']
    return redirect('home')

def login_view(request):
    error = None
    if request.method == "POST":
        u = request.POST.get('username')
        p = request.POST.get('password')
        user = authenticate(request, username=u, password=p)
        if user:
            if EmailAddress.objects.filter(user=user, verified=True).exists():
                login(request, user)
                return redirect('dashboard')
            else: 
                error = "Verify email first."
        else: 
            error = "Invalid login."
    return render(request, 'core/login.html', {'error': error})

def signup_view(request):
    error = None
    if request.method == "POST":
        u = request.POST.get('username')
        e = request.POST.get('email')
        p = request.POST.get('password')
        if User.objects.filter(username=u).exists(): 
            error = "Username taken."
        elif User.objects.filter(email=e).exists(): 
            error = "Email registered."
        else:
            try:
                validate_password(p)
            except ValidationError as exc:
                error = " ".join(exc.messages)
                
            if not error:
                user = User.objects.create_user(username=u, email=e, password=p)
                email_address = EmailAddress.objects.create(user=user, email=e, primary=True, verified=False)
                email_address.send_confirmation(request)
                return redirect('login')
    return render(request, 'core/signup.html', {'error': error})

def logout_view(request):
    logout(request)
    return redirect('login')

def custom_404(request, exception):
    return render(request, 'core/404.html', status=404)

def custom_500(request):
    return render(request, 'core/500.html', status=500)

from django.contrib.admin.views.decorators import staff_member_required
from django.core.mail import EmailMessage
import csv

@staff_member_required
def export_csv_email(request):
    import io
    csv_file = io.StringIO()
    writer = csv.writer(csv_file)
    writer.writerow(['game_choice', 'username', 'platform', 'date', 'm1', 'm2', 'm3', 'm4', 'm5', 'm6', 'm7', 'm8'])
    for snap in CrowdsourcedStatSnapshot.objects.all():
        writer.writerow([snap.game_choice, snap.username, snap.platform, snap.date, snap.m1, snap.m2, snap.m3, snap.m4, snap.m5, snap.m6, snap.m7, snap.m8])
    
    email = EmailMessage(
        'Database CSV Export',
        'Attached is the latest AI tracking data.',
        settings.DEFAULT_FROM_EMAIL,
        [request.user.email]
    )
    email.attach('ai_data.csv', csv_file.getvalue(), 'text/csv')
    email.send()
    messages.success(request, "CSV Export emailed successfully.")
    return redirect('dashboard')
