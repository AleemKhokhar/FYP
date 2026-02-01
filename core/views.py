from django.shortcuts import render
from django.http import HttpResponse
import requests

def home(request):
    return render(request, "core/home.html")

def game_search(request):
    query = request.GET.get('q')
    api_key = '53d74ce63dbd4a3794ac77648e8edfc2'
    print(f"DEBUG: User searched for {query}")
    
    url = f"https://api.rawg.io/api/games?key={api_key}&search={query}"
    
    response = requests.get(url)
    data = response.json()
    games = data.get('results', [])
    if games:
        print(f"Top result: {games[0]['name']}")
    return render(request, 'core/results.html', {'games': games, 'query': query})