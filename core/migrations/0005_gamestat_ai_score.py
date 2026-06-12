from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_gamestat_metric_1_gamestat_metric_2_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='gamestat',
            name='ai_score',
            field=models.FloatField(default=0.0),
        ),
    ]
