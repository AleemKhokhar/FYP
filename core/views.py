from django.shortcuts import render
from django.http import HttpResponse
import requests

def home(request):
    return render(request, "core/home.html")

def game_search(request):
    username = request.GET.get('q')
    platform = request.GET.get('platform')
    api_key = '6985c7e9-4313-40ad-ac49-507f9dbb1ba0'
    
    url = f"https://api.fortnitetracker.com/v1/profile/{platform}/{username}"
    
    headers = {
        'TRN-Api-Key': api_key,
        'Accept': 'application/json'
    }
    response = requests.get(url, headers=headers)
    data = response.json()
    
    stats_list = data.get('lifeTimeStats', [])
    
    time_played = "Not Found"
    for s in stats_list:
        if s['key'] == 'Time Played':
            time_played = s['value']
    
    print(f"DEBUG: Found {time_played} for {username}")
    
    return render(request, 'core/results.html', {
        'username': username,
        'platform': platform,
        'time_played': time_played,
        'all_stats': stats_list
    })