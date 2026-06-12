from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_rename_hours_played_gamestat_platform_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='gamestat',
            name='metric_1',
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name='gamestat',
            name='metric_2',
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name='gamestat',
            name='metric_3',
            field=models.FloatField(default=0.0),
        ),
    ]
