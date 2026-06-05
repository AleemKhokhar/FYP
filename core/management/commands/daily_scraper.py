import os
import requests
import time
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
                time.sleep(1.5) 
                
                if not profile_resp.get("success"):
                    cause = profile_resp.get('cause', 'Unknown')
                    self.stdout.write(f"API Rejection for {player.username}: {cause}")
                    
                    if "daily" in cause.lower():
                        self.stdout.write("Daily limit reached. Stopping scrape for today.")
                        return
                        
                    if "throttle" in cause.lower():
                        self.stdout.write("Sleeping for 60 seconds to reset rate limit...")
                        time.sleep(60)
                    continue
                
                player_resp = requests.get(player_url).json()
                time.sleep(1.5)
                
                if not profile_resp.get("profiles"):
                    self.stdout.write(f"No Skyblock profiles found for {player.username}, skipping...")
                    continue
                
                profile = next((p for p in profile_resp["profiles"] if p.get("selected")), profile_resp["profiles"][0])
                
                clean_uuid = player.uuid.replace('-', '')
                member_data = profile.get("members", {}).get(clean_uuid, {})
                
                if not member_data:
                    self.stdout.write(f"Could not find member data for {player.username}, skipping...")
                    continue
                
                last_login_ms = 0
                if player_resp.get("success") and player_resp.get("player"):
                    last_login_ms = player_resp["player"].get("lastLogin", 0)
                
                if last_login_ms > 0:
                    last_login_date = datetime.datetime.fromtimestamp(last_login_ms / 1000.0, tz=datetime.timezone.utc)
                    if last_login_date < fourteen_days_ago:
                        player.is_active = False
                        player.save()
                        self.stdout.write(f"Deactivated {player.username} (Inactive since {last_login_date.date()})")
                        continue
                
                player_data_dict = member_data.get('player_data', {})
                experience_data = player_data_dict.get('experience', {})
                
                combat_xp = experience_data.get("SKILL_COMBAT", 0)
                mining_xp = experience_data.get("SKILL_MINING", 0)
                farming_xp = experience_data.get("SKILL_FARMING", 0)
                foraging_xp = experience_data.get("SKILL_FORAGING", 0)
                fishing_xp = experience_data.get("SKILL_FISHING", 0)
                
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