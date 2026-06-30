from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from core.models import DailyStatSnapshot, CrowdsourcedStatSnapshot, SavedGame

class Command(BaseCommand):
    help = 'Re-migrates old DailyStatSnapshot data and correctly spaces out dates to recover lost historical data.'

    def handle(self, *args, **options):
        self.stdout.write("Wiping old botched migration data...")
        CrowdsourcedStatSnapshot.objects.filter(game_choice='hypixel').delete()
        
        self.stdout.write("Re-migrating Hypixel data from the original database...")
        

        player_ids = DailyStatSnapshot.objects.values_list('player_id', flat=True).distinct()
        
        migrated = 0
        skipped = 0
        
        today = timezone.now().date()
        
        for p_id in player_ids:
            try:
                with transaction.atomic():

                    snaps = list(DailyStatSnapshot.objects.filter(player_id=p_id).order_by('id'))
                    count = len(snaps)
                    
                    if count == 0:
                        continue
                        
                    username = snaps[0].player.username
                    
                    for snap in snaps:
                        CrowdsourcedStatSnapshot.objects.create(
                            game_choice='hypixel',
                            username=username,
                            date=snap.date,
                            m1=snap.skyblock_xp,
                            m2=snap.combat_xp,
                            m3=snap.catacombs_xp,
                            m4=snap.mining_xp,
                            m5=snap.farming_xp,
                            m6=snap.foraging_xp,
                            m7=snap.fishing_xp,
                            m8=0.0
                        )
                        migrated += 1
                        
                    self.stdout.write(f"Recovered {count} historical records for {username}.")
            except Exception as e:
                skipped += 1
                self.stdout.write(self.style.WARNING(f"Skipped player ID {p_id} (Error: {e})"))
                
        self.stdout.write(self.style.SUCCESS(f"Successfully recovered {migrated} total historical records!"))
