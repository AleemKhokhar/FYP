from django.db import models
from django.contrib.auth.models import User

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    avatar = models.ImageField(default='profile_pics/default.jpg', upload_to='profile_pics')
    bio = models.TextField(max_length=500, blank=True)
    theme_color = models.CharField(max_length=7, default='#00ff88')

    def __str__(self):
        return f'{self.user.username} Profile'


class SavedGame(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    game_username = models.CharField(max_length=100)
    platform = models.CharField(max_length=50)
    time_played = models.CharField(max_length=100, null=True, blank=True)
    sim = models.FloatField(default=0.0)
    m1 = models.CharField(max_length=100, null=True, blank=True)
    m2 = models.CharField(max_length=100, null=True, blank=True)
    m3 = models.CharField(max_length=100, null=True, blank=True)
    date_saved = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'game_username', 'platform')

    def __str__(self):
        return f"{self.user.username} - {self.game_username} ({self.platform})"

from django.db import models

class APILog(models.Model):
    endpoint = models.CharField(max_length=255)
    status_code = models.IntegerField()
    response_time = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)

class TrackedPlayer(models.Model):
    uuid = models.CharField(max_length=100, unique=True)
    username = models.CharField(max_length=100)
    profile_id = models.CharField(max_length=100, default='pending')
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.username


class DailyStatSnapshot(models.Model):
    player = models.ForeignKey(TrackedPlayer, on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)
    
    catacombs_xp = models.FloatField(default=0.0)
    combat_xp = models.FloatField(default=0.0)
    mining_xp = models.FloatField(default=0.0)
    farming_xp = models.FloatField(default=0.0)
    foraging_xp = models.FloatField(default=0.0)
    fishing_xp = models.FloatField(default=0.0)
    skyblock_xp = models.FloatField(default=0.0)
    
    bank_balance = models.FloatField(default=0.0)
    purse_balance = models.FloatField(default=0.0)

    def __str__(self):
        return f"{self.player.username} - {self.date}"

import datetime

class CrowdsourcedStatSnapshot(models.Model):
    game_choice = models.CharField(max_length=50)
    username = models.CharField(max_length=100)
    platform = models.CharField(max_length=50, blank=True, null=True)
    date = models.DateField(default=datetime.date.today)
    
    m1 = models.FloatField(default=0.0)
    m2 = models.FloatField(default=0.0)
    m3 = models.FloatField(default=0.0)
    m4 = models.FloatField(default=0.0)
    m5 = models.FloatField(default=0.0)
    m6 = models.FloatField(default=0.0)
    m7 = models.FloatField(default=0.0)
    m8 = models.FloatField(default=0.0)

    class Meta:
        unique_together = ('game_choice', 'username', 'date')

    def __str__(self):
        return f"{self.game_choice} | {self.username} | {self.date}"