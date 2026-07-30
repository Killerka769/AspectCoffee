
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('catalog', '0007_delete_parselog_product_altitude_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='StockItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('qty', models.PositiveIntegerField(default=0, verbose_name='Текущий остаток')),
                ('min_qty', models.PositiveIntegerField(default=5, help_text='При падении ниже этого значения — алерт администратору', verbose_name='Минимальный остаток')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Обновлён')),
                ('variant', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='stock', to='catalog.productvariant', verbose_name='Вариант товара')),
            ],
            options={
                'verbose_name': 'Остаток на складе',
                'verbose_name_plural': 'Остатки на складе',
            },
        ),
    ]
