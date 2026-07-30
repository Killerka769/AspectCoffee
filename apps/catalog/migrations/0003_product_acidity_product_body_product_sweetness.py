
import django.core.validators
from django.db import migrations, models
class Migration(migrations.Migration):
    dependencies = [
        ('catalog', '0002_initial'),
    ]
    operations = [
        migrations.AddField(
            model_name='product',
            name='acidity',
            field=models.PositiveIntegerField(default=5, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(10)], verbose_name='Кислотность'),
        ),
        migrations.AddField(
            model_name='product',
            name='body',
            field=models.PositiveIntegerField(default=5, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(10)], verbose_name='Плотность (Тельце)'),
        ),
        migrations.AddField(
            model_name='product',
            name='sweetness',
            field=models.PositiveIntegerField(default=5, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(10)], verbose_name='Сладость'),
        ),
    ]
