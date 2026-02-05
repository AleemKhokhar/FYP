from django.db import models
from django.contrib.auth.models import User
class GameStat(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    game_username = models.CharField(max_length=100)
    platform = models.CharField(max_length=50)
    time_played = models.CharField(max_length=50)
    date_saved = models.DateTimeField(auto_now_add=True)
