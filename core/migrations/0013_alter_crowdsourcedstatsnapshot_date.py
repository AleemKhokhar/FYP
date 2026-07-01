import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0012_crowdsourcedstatsnapshot'),
    ]

    operations = [
        migrations.AlterField(
            model_name='crowdsourcedstatsnapshot',
            name='date',
            field=models.DateField(default=datetime.date.today),
        ),
    ]
