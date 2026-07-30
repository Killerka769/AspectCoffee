# Generated manually 2026-07-05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0036_payment_timeout'),
    ]

    operations = [
        migrations.AddField(
            model_name='review',
            name='delivery_operator',
            field=models.CharField(
                blank=True,
                default='',
                max_length=100,
                verbose_name='Оператор доставки',
                help_text='Например: Aspect Coffee, СДЭК, Почта России, OZON, WB',
            ),
        ),
    ]
