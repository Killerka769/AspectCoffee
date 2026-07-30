
from django.db import migrations, models
class Migration(migrations.Migration):
    dependencies = [
        ('catalog', '0004_product_flavor_description_html_and_more'),
    ]
    operations = [
        migrations.AlterField(
            model_name='product',
            name='roast_level',
            field=models.CharField(blank=True, choices=[('light', 'Светлая'), ('medium', 'Средняя'), ('dark', 'Тёмная'), ('espresso', 'Эспрессо')], max_length=32, verbose_name='Степень обжарки'),
        ),
    ]
