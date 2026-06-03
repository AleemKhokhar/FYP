from django.contrib import admin
from .models import SavedGame, Profile

@admin.register(SavedGame)
class SavedGameAdmin(admin.ModelAdmin):
    list_display = ('game_username', 'platform', 'ai_score', 'user', 'date_saved')
    list_filter = ('platform', 'date_saved')
    search_fields = ('game_username', 'user__username')
    ordering = ('-date_saved',)
    readonly_fields = ('date_saved',)

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user',)
    
from django.db import models

class APILog(models.Model):
    endpoint = models.CharField(max_length=255)
    status_code = models.IntegerField()
    response_time = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)