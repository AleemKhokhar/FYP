from django.db import models
from django.contrib.auth.models import User

class GameStat(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    game_username = models.CharField(max_length=100)
    platform = models.CharField(max_length=50)
    time_played = models.CharField(max_length=50)
    metric_1 = models.FloatField(default=0.0)
    metric_2 = models.FloatField(default=0.0)
    metric_3 = models.FloatField(default=0.0)
    date_saved = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.platform}"