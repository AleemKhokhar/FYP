from django.contrib import admin
from .models import GameStat

@admin.register(GameStat)
class GameStatAdmin(admin.ModelAdmin):
    list_display = ('user', 'game_username', 'platform', 'metric_1', 'metric_2', 'metric_3')