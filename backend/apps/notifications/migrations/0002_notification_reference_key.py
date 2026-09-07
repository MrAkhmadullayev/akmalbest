"""Bildirishnomalar takrorlanmasligi uchun dedublikatsiya kaliti."""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("notifications", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="notification",
            name="reference_key",
            field=models.CharField(blank=True, db_index=True, max_length=100),
        ),
    ]
