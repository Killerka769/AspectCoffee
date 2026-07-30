
import django.core.validators
from django.db import migrations, models
class Migration(migrations.Migration):
    dependencies = [
        ('catalog', '0003_product_acidity_product_body_product_sweetness'),
    ]
    operations = [
        migrations.AddField(
            model_name='product',
            name='flavor_description_html',
            field=models.TextField(blank=True, verbose_name='Описание вкуса (HTML с баджами)'),
        ),
        migrations.AddField(
            model_name='product',
            name='processing_method',
            field=models.CharField(blank=True, max_length=100, verbose_name='Метод обработки'),
        ),
        migrations.AlterField(
            model_name='product',
            name='acidity',
            field=models.PositiveIntegerField(default=5, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(10)], verbose_name='Кислотность'),
        ),
        migrations.AlterField(
            model_name='product',
            name='body',
            field=models.PositiveIntegerField(default=5, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(10)], verbose_name='Плотность (Тельце)'),
        ),
        migrations.AlterField(
            model_name='product',
            name='roast_level',
            field=models.CharField(blank=True, max_length=100, verbose_name='Степень обжарки'),
        ),
        migrations.AlterField(
            model_name='product',
            name='sweetness',
            field=models.PositiveIntegerField(default=0, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(10)], verbose_name='Сладость'),
        ),
    ]
