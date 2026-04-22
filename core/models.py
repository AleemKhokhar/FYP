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
    ai_score = models.FloatField(default=0.0)
    m1 = models.CharField(max_length=100, null=True, blank=True)
    m2 = models.CharField(max_length=100, null=True, blank=True)
    m3 = models.CharField(max_length=100, null=True, blank=True)
    date_saved = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'game_username', 'platform')

    def __str__(self):
        return f"{self.user.username} - {self.game_username} ({self.platform})"