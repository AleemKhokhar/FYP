import json
from django.core.management.base import BaseCommand
from core.models import TrackedPlayer

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        with open('verified_uuids.json', 'r') as file:
            data = json.load(file)
        
        added_count = 0
        for username, uuid in data.items():
            obj, created = TrackedPlayer.objects.get_or_create(
                uuid=uuid,
                defaults={
                    'username': username,
                    'profile_id': 'pending'
                }
            )
            if created:
                added_count += 1
                
        self.stdout.write(f"Successfully imported {added_count} players into the database!")