import os
import requests
import json
from pathlib import Path
from dotenv import load_dotenv
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Scrapes all member tags from a Clash of Clans clan."

    def add_arguments(self, parser):
        parser.add_argument('clan_tag', type=str, help='The clan tag (e.g. #2Q2Q90JRC or 2Q2Q90JRC)')

    def handle(self, *args, **kwargs):

        env_path = Path(__file__).resolve().parent.parent.parent.parent / ".env"
        load_dotenv(env_path, override=True)
        
        clan_tag = kwargs['clan_tag']
        api_key = os.environ.get('CLASH_API_KEY')
        
        if not api_key:
            self.stdout.write(self.style.ERROR("Error: CLASH_API_KEY environment variable is not set in .env"))
            return
            
        clean_tag = clan_tag.replace("#", "").upper()
        url = f"https://cocproxy.royaleapi.dev/v1/clans/%23{clean_tag}/members"
        headers = {"Authorization": f"Bearer {api_key}"}
        
        self.stdout.write(f"Fetching members for clan #{clean_tag}...")
        
        try:
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code != 200:
                self.stdout.write(self.style.ERROR(f"Error fetching clan: {r.status_code} - {r.text}"))
                return
                
            data = r.json()
            items = data.get("items", [])
            
            tags = [member.get("tag") for member in items if member.get("tag")]
            
            if not tags:
                self.stdout.write(self.style.WARNING("No members found or invalid response format."))
                return
                
            filename = "scraped_clan_tags.json"
            

            existing_tags = []
            if os.path.exists(filename):
                try:
                    with open(filename, 'r') as f:
                        existing_tags = json.load(f)
                except json.JSONDecodeError:
                    pass
            

            all_tags = list(set(existing_tags + tags))
            
            with open(filename, 'w') as f:
                json.dump(all_tags, f, indent=4)
                
            self.stdout.write(self.style.SUCCESS(f"Successfully scraped {len(tags)} members from #{clean_tag}."))
            self.stdout.write(self.style.SUCCESS(f"File '{filename}' now contains {len(all_tags)} total unique tags."))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Exception occurred: {e}"))
