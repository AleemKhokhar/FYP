import os
import django
import sys

sys.path.append(r'c:\Users\aleem_rmv7k3n\Documents\FYP')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_project.settings')
django.setup()

from core.models import SavedGame

def dump_db():
    print("--- DUMPING SAVED GAMES ---")
    for sg in SavedGame.objects.all():
        print(f"User: {sg.user.username} | GameUser: {sg.game_username} | Platform: '{sg.platform}' | m1: '{sg.m1}' | m2: '{sg.m2}' | m3: '{sg.m3}'")

if __name__ == '__main__':
    dump_db()
