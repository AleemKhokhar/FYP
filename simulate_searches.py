import json
import requests
import time

def main():
    print("\nWhich game are you simulating? (e.g. fortnite, steam, clash)")
    game_choice = input("Enter game: ").strip().lower()
    
    if not game_choice:
        game_choice = "fortnite"

    print(f"\nWhat is the name of your JSON file? (default: {game_choice}_usernames.json)")
    filename = input("Enter filename: ").strip()
    if not filename:
        filename = f"{game_choice}_usernames.json"

    try:
        with open(filename, 'r', encoding='utf-8') as f:
            usernames = json.load(f)
    except FileNotFoundError:
        print(f"Error: {filename} not found! Please create it first.")
        return

    print(f"\nLoaded {len(usernames)} {game_choice} usernames.")
    
    print("\nWhere do you want to send these searches?")
    print("Example: https://your-app-name.onrender.com (or leave blank for local dev)")
    base_url = input("Enter website URL: ").strip()
    
    if not base_url:
        base_url = "http://127.0.0.1:8000"
    
    if base_url.endswith('/'):
        base_url = base_url[:-1]

    print(f"\nStarting automated browser simulation against {base_url}...\n")

    successful = 0
    failed = 0

    for username in usernames:
        url = f"{base_url}/search/?game_choice={game_choice}&username={username}&platform=epic"
        
        try:
            print(f"Searching for '{username}'...", end=" ", flush=True)
            r = requests.get(url)
            
            # The website returns 200 OK if it finds the player and successfully renders the results page
            if r.status_code == 200:
                print("SUCCESS (Saved to DB!)")
                successful += 1
            else:
                print(f"FAILED (Not found or error {r.status_code})")
                failed += 1
                
        except requests.exceptions.ConnectionError:
            print("ERROR: Could not connect to your website. Make sure 'python manage.py runserver' is running!")
            return
            
        # Wait 1.5 seconds between searches so we don't accidentally get IP banned by Fortnite APIs
        time.sleep(1.5)

    print("\n--- Simulation Complete ---")
    print(f"Successfully simulated and crowdsourced {successful} players!")
    print(f"Failed to find {failed} players.")

if __name__ == "__main__":
    main()
