from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_trackedplayer_dailystatsnapshot'),
    ]

    operations = [
        migrations.AddField(
            model_name='dailystatsnapshot',
            name='bank_balance',
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name='dailystatsnapshot',
            name='catacombs_xp',
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name='dailystatsnapshot',
            name='combat_xp',
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name='dailystatsnapshot',
            name='farming_xp',
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name='dailystatsnapshot',
            name='fishing_xp',
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name='dailystatsnapshot',
            name='foraging_xp',
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name='dailystatsnapshot',
            name='mining_xp',
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name='dailystatsnapshot',
            name='purse_balance',
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name='dailystatsnapshot',
            name='skyblock_xp',
            field=models.FloatField(default=0.0),
        ),
    ]
