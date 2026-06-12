from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0010_dailystatsnapshot_bank_balance_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='APILog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('endpoint', models.CharField(max_length=255)),
                ('status_code', models.IntegerField()),
                ('response_time', models.FloatField()),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]
