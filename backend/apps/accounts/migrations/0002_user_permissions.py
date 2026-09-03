"""Foydalanuvchiga modul bo'yicha ruxsatlar maydonini qo'shish.

Qo'lda yozilgan migratsiya (sandbox'da `makemigrations` ishlamaydi).
Maydon `default=dict` bilan qo'shiladi, ya'ni mavjud foydalanuvchilarda `{}`
bo'lib qoladi va ular rol standartlari bo'yicha ishlashda davom etadi.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='permissions',
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
