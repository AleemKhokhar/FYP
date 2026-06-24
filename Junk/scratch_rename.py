import os
import glob

base_dir = r"c:\Users\aleem_rmv7k3n\Documents\FYP\core"

files_to_update = [
    r"views.py",
    r"ai_model.py",
    r"admin.py",
    r"templates\core\dashboard.html",
    r"templates\core\comparison.html",
    r"templates\core\results.html",
    r"templates\core\leaderboard.html",
    r"templates\core\pdf_template.html",
]

for file_rel in files_to_update:
    path = os.path.join(base_dir, file_rel)
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Simple text replacement
        new_content = content.replace('ai_score', 'sim')
        
        if new_content != content:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"Updated {file_rel}")
        else:
            print(f"No changes needed for {file_rel}")
    else:
        print(f"File not found: {path}")

print("Done.")
