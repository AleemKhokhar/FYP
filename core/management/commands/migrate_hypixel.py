from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import DailyStatSnapshot, CrowdsourcedStatSnapshot

class Command(BaseCommand):
    help = 'Migrates old DailyStatSnapshot hypixel data to the new generic CrowdsourcedStatSnapshot table.'

    def handle(self, *args, **options):
        old_snaps = DailyStatSnapshot.objects.select_related('player').all()
        count = old_snaps.count()
        
        self.stdout.write(f"Found {count} old Hypixel snapshots. Migrating with atomic transactions...")
        
        migrated = 0
        skipped = 0
        
        with transaction.atomic():
            for snap in old_snaps:
                try:
                    if CrowdsourcedStatSnapshot.objects.filter(
                        game_choice='hypixel', 
                        username=snap.player.username, 
                        date=snap.date
                    ).exists():
                        skipped += 1
                        continue
                        
                    CrowdsourcedStatSnapshot.objects.create(
                        game_choice='hypixel',
                        username=snap.player.username,
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
                    self.stdout.write(f"[{migrated}/{count}] Migrated {snap.player.username} for {snap.date}")
                except Exception as e:
                    skipped += 1
                    self.stdout.write(self.style.WARNING(f"Skipped {snap.player.username} for {snap.date} (Error/Duplicate)"))
                
        self.stdout.write(self.style.SUCCESS(f"Successfully migrated {migrated} records. Skipped {skipped} (likely duplicates)."))
