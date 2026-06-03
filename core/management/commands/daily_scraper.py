import requests
import time
import os
import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from core.models import TrackedPlayer, DailyStatSnapshot

class Command(BaseCommand):
    
    def handle(self, *args, **kwargs):
        api_key = os.environ.get('HYPIXEL_API_KEY')
        
        if not api_key:
            self.stdout.write("Error: HYPIXEL_API_KEY environment variable is not set.")
            return
            
        active_players = TrackedPlayer.objects.filter(is_active=True)
        self.stdout.write(f"Starting scrape for {active_players.count()} active players...")
        
        fourteen_days_ago = timezone.now() - timedelta(days=14)
        
        for player in active_players:
            profile_url = f"https://api.hypixel.net/v2/skyblock/profiles?key={api_key}&uuid={player.uuid}"
            player_url = f"https://api.hypixel.net/v2/player?key={api_key}&uuid={player.uuid}"
            
            try:
                profile_resp = requests.get(profile_url).json()
                time.sleep(0.5) 
                
                player_resp = requests.get(player_url).json()
                time.sleep(0.5)
                
                if not profile_resp.get("success") or not profile_resp.get("profiles"):
                    continue
                
                profile = next((p for p in profile_resp["profiles"] if p.get("selected")), profile_resp["profiles"][0])
                
                
                clean_uuid = player.uuid.replace('-', '')
                member_data = profile.get("members", {}).get(clean_uuid, {})
                
                if not member_data:
                    self.stdout.write(f"Could not find member data for {player.username}, skipping...")
                    continue
                
                
                last_login_ms = 0
                combat_xp = 0
                mining_xp = 0
                farming_xp = 0
                foraging_xp = 0
                fishing_xp = 0
                
                if player_resp.get("success") and player_resp.get("player"):
                    player_data = player_resp["player"]
                    last_login_ms = player_data.get("lastLogin", 0)
                    
                    skills = player_data.get("player_data", {}).get("experience", {})
                    combat_xp = skills.get("SKILL_COMBAT", 0)
                    mining_xp = skills.get("SKILL_MINING", 0)
                    farming_xp = skills.get("SKILL_FARMING", 0)
                    foraging_xp = skills.get("SKILL_FORAGING", 0)
                    fishing_xp = skills.get("SKILL_FISHING", 0)
                
                
                if last_login_ms > 0:
                    last_login_date = datetime.datetime.fromtimestamp(last_login_ms / 1000.0, tz=datetime.timezone.utc)
                    if last_login_date < fourteen_days_ago:
                        player.is_active = False
                        player.save()
                        self.stdout.write(f"Deactivated {player.username} (Inactive since {last_login_date.date()})")
                        continue
                
                cata_xp = member_data.get("dungeons", {}).get("dungeon_types", {}).get("catacombs", {}).get("experience", 0)
                skyblock_xp = member_data.get("leveling", {}).get("experience", 0)
                purse = member_data.get("coin_purse", 0)
                
                DailyStatSnapshot.objects.create(
                    player=player,
                    catacombs_xp=cata_xp,
                    skyblock_xp=skyblock_xp,
                    purse_balance=purse,
                    combat_xp=combat_xp,
                    mining_xp=mining_xp,
                    farming_xp=farming_xp,
                    foraging_xp=foraging_xp,
                    fishing_xp=fishing_xp
                )
                
                self.stdout.write(f"Saved stats for {player.username}")
                
            except Exception as e:
                self.stdout.write(f"Error scraping {player.username}: {str(e)}")