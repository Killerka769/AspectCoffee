
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('orders', '0004_remove_cartitem_grind_remove_orderitem_grind'),
    ]

    operations = [
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('yookassa_id', models.CharField(blank=True, db_index=True, max_length=100, unique=True, verbose_name='ID платежа (ЮKassa)')),
                ('yookassa_refund_id', models.CharField(blank=True, max_length=100, verbose_name='ID возврата (ЮKassa)')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12, verbose_name='Сумма')),
                ('status', models.CharField(choices=[('pending', 'Ожидает оплаты'), ('succeeded', 'Оплачен'), ('cancelled', 'Отменён'), ('refunded', 'Возвращён')], db_index=True, default='pending', max_length=20, verbose_name='Статус')),
                ('confirmation_url', models.URLField(blank=True, verbose_name='URL подтверждения')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Создан')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Обновлён')),
                ('order', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='payment', to='orders.order', verbose_name='Заказ')),
            ],
            options={
                'verbose_name': 'Платёж',
                'verbose_name_plural': 'Платежи',
                'ordering': ['-created_at'],
            },
        ),
    ]
