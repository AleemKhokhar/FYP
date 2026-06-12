from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_savedgame_delete_gamestat'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='avatar',
            field=models.ImageField(default='profile_pics/default.jpg', upload_to='profile_pics'),
        ),
    ]
