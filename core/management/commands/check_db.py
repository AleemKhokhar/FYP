import os
from django.core.management.base import BaseCommand
from core.models import CrowdsourcedStatSnapshot

class Command(BaseCommand):
    help = "Checks database statistics for AI training readiness."

    def handle(self, *args, **kwargs):
        games = ['hypixel', 'fortnite', 'clash', 'steam']
        
        for game in games:
            snaps = CrowdsourcedStatSnapshot.objects.filter(game_choice=game)
            total_snaps = snaps.count()
            

            player_groups = {}
            for snap in snaps:
                if snap.username not in player_groups:
                    player_groups[snap.username] = set()
                player_groups[snap.username].add(snap.date)
                
            unique_players = len(player_groups)
            
            eligible_players = 0
            for username, dates in player_groups.items():
                if len(dates) >= 2:
                    eligible_players += 1
                    
            self.stdout.write(self.style.SUCCESS(f"\n--- Database Stats for '{game}' ---"))
            self.stdout.write(f"Total Snapshots: {total_snaps}")
            self.stdout.write(f"Unique Players Logged: {unique_players}")
            
            if eligible_players >= 100:
                self.stdout.write(self.style.SUCCESS(f"Players eligible for AI training (2+ dates): {eligible_players} / 100"))
            else:
                self.stdout.write(self.style.WARNING(f"Players eligible for AI training (2+ dates): {eligible_players} / 100"))
                
        self.stdout.write(self.style.NOTICE("\nNote: Any player with only 1 date must be searched again tomorrow (or via a scraper) to get their 2nd date and make them eligible!"))
