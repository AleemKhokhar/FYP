from django.shortcuts import render
from django.http import HttpResponse

def home(request):
    return render(request, "core/home.html")

def game_search(request):
    query = request.GET.get('q')
    print(f"DEBUG: User searched for {query}")
    
    if query:
        return HttpResponse(f"The Brain caught your word! You are looking for: {query}")
    else:
        return HttpResponse("Please type something in the search box!")