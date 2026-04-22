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