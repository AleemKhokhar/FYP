# Generated manually
from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_savedgame_delete_gamestat'),
    ]

    operations = [
        migrations.RenameField(
            model_name='savedgame',
            old_name='ai_score',
            new_name='sim',
        ),
    ]
