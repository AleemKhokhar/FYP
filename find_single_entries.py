import os
import django
import json

def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_project.settings')
    django.setup()

    from core.models import CrowdsourcedStatSnapshot
    from django.db.models import Count

    print("\nWhich game do you want to check? (e.g. fortnite, steam, clash)")
    game_choice = input("Enter game: ").strip().lower()
    if not game_choice:
        game_choice = "fortnite"

    # Find players for this game who only have exactly 1 snapshot entry
    players = CrowdsourcedStatSnapshot.objects.filter(game_choice=game_choice).values('username', 'platform').annotate(
        snap_count=Count('id')
    ).filter(snap_count=1)

    count = players.count()
    print(f"\nFound {count} players in your LIVE database for '{game_choice}' who only have a single entry.")

    if count > 0:
        results = [p['username'] for p in players]
        filename = f"{game_choice}_single_entries.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=4, ensure_ascii=False)
            
        print(f"Success! I saved exactly who they are into '{filename}' so you can see them.")
    else:
        print("Everyone has 2+ entries!")

if __name__ == "__main__":
    main()
