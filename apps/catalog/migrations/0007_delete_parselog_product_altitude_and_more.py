
from django.db import migrations, models
class Migration(migrations.Migration):
    dependencies = [
        ('catalog', '0006_parselog'),
    ]
    operations = [
        migrations.DeleteModel(
            name='ParseLog',
        ),
        migrations.AddField(
            model_name='product',
            name='altitude',
            field=models.CharField(blank=True, max_length=100, verbose_name='Высота произрастания'),
        ),
        migrations.AddField(
            model_name='product',
            name='caffeine_content',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=4, null=True, verbose_name='Содержание кофеина (%)'),
        ),
        migrations.AddField(
            model_name='product',
            name='q_score',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=4, null=True, verbose_name='Оценка Q-грейдера'),
        ),
        migrations.AddField(
            model_name='product',
            name='region',
            field=models.CharField(blank=True, max_length=200, verbose_name='Регион'),
        ),
        migrations.AddField(
            model_name='product',
            name='roaster_machine',
            field=models.CharField(blank=True, max_length=100, verbose_name='Ростер для обжарки'),
        ),
    ]
