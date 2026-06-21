import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_project.settings')
django.setup()

from core.models import DailyStatSnapshot
dates = list(DailyStatSnapshot.objects.values_list('date', flat=True).distinct())
print(f"DISTINCT DATES IN OLD TABLE: {dates}")

from core.models import CrowdsourcedStatSnapshot
new_dates = list(CrowdsourcedStatSnapshot.objects.values_list('date', flat=True).distinct())
print(f"DISTINCT DATES IN NEW TABLE: {new_dates}")
