
import django.core.validators
from django.db import migrations, models
class Migration(migrations.Migration):
    initial = True
    dependencies = [
    ]
    operations = [
        migrations.CreateModel(
            name='Banner',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200, verbose_name='Заголовок')),
                ('subtitle', models.CharField(blank=True, max_length=300, verbose_name='Подзаголовок')),
                ('link', models.URLField(blank=True, verbose_name='Ссылка')),
                ('is_active', models.BooleanField(default=True, verbose_name='Активен')),
                ('show_from', models.DateTimeField(blank=True, null=True, verbose_name='Показывать с')),
                ('show_to', models.DateTimeField(blank=True, null=True, verbose_name='Показывать по')),
                ('order', models.PositiveIntegerField(default=0, verbose_name='Порядок')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Баннер',
                'verbose_name_plural': 'Баннеры',
                'ordering': ['order'],
            },
        ),
        migrations.CreateModel(
            name='Cart',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('session_key', models.CharField(blank=True, db_index=True, max_length=40, null=True, verbose_name='Ключ сессии')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Корзина',
                'verbose_name_plural': 'Корзины',
            },
        ),
        migrations.CreateModel(
            name='CartItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('qty', models.PositiveIntegerField(default=1, validators=[django.core.validators.MinValueValidator(1)], verbose_name='Количество')),
            ],
            options={
                'verbose_name': 'Позиция корзины',
                'verbose_name_plural': 'Позиции корзины',
            },
        ),
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('new', 'Новый'), ('paid', 'Оплачен'), ('assembling', 'В сборке'), ('shipped', 'Передан в доставку'), ('delivered', 'Доставлен'), ('completed', 'Завершён'), ('cancelled', 'Отменён')], db_index=True, default='new', max_length=20, verbose_name='Статус')),
                ('delivery_type', models.CharField(choices=[('pickup', 'Самовывоз'), ('courier', 'Курьер по городу'), ('cdek_pvz', 'СДЭК — до ПВЗ'), ('cdek_door', 'СДЭК — курьером до двери')], max_length=20, verbose_name='Тип доставки')),
                ('delivery_address', models.JSONField(default=dict, verbose_name='Адрес доставки')),
                ('delivery_cost', models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='Стоимость доставки')),
                ('cdek_track_number', models.CharField(blank=True, max_length=100, verbose_name='Трек-номер СДЭК')),
                ('cdek_order_uuid', models.UUIDField(blank=True, null=True, verbose_name='UUID заказа СДЭК')),
                ('payment_method', models.CharField(choices=[('card', 'Банковская карта'), ('sbp', 'СБП'), ('cod', 'При получении')], max_length=10, verbose_name='Способ оплаты')),
                ('payment_status', models.CharField(choices=[('pending', 'Ожидает оплаты'), ('paid', 'Оплачен'), ('refunded', 'Возвращён')], default='pending', max_length=20, verbose_name='Статус оплаты')),
                ('payment_id', models.CharField(blank=True, max_length=100, verbose_name='ID платежа (шлюз)')),
                ('discount_amount', models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='Скидка')),
                ('total_amount', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Итог')),
                ('contact_name', models.CharField(blank=True, max_length=200, verbose_name='Имя получателя')),
                ('contact_phone', models.CharField(blank=True, max_length=20, verbose_name='Телефон получателя')),
                ('contact_email', models.EmailField(blank=True, max_length=254, verbose_name='Email получателя')),
                ('comment', models.TextField(blank=True, verbose_name='Комментарий к заказу')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Создан')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Обновлён')),
            ],
            options={
                'verbose_name': 'Заказ',
                'verbose_name_plural': 'Заказы',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='OrderItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('product_name', models.CharField(max_length=300, verbose_name='Название товара (снимок)')),
                ('variant_description', models.CharField(max_length=200, verbose_name='Описание варианта (снимок)')),
                ('qty', models.PositiveIntegerField(verbose_name='Количество')),
                ('price_at_order', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Цена на момент заказа')),
            ],
            options={
                'verbose_name': 'Позиция заказа',
                'verbose_name_plural': 'Позиции заказа',
            },
        ),
        migrations.CreateModel(
            name='PromoCode',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(db_index=True, max_length=50, unique=True, verbose_name='Код')),
                ('discount_type', models.CharField(choices=[('percent', 'Процент (%)'), ('fixed', 'Фиксированная сумма (₽)')], max_length=10, verbose_name='Тип скидки')),
                ('discount_value', models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(0)], verbose_name='Размер скидки')),
                ('valid_from', models.DateTimeField(verbose_name='Действует с')),
                ('valid_to', models.DateTimeField(verbose_name='Действует по')),
                ('usage_limit', models.PositiveIntegerField(blank=True, null=True, verbose_name='Лимит использований')),
                ('used_count', models.PositiveIntegerField(default=0, verbose_name='Использований')),
                ('min_order_amount', models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='Минимальная сумма заказа')),
                ('is_active', models.BooleanField(default=True, verbose_name='Активен')),
            ],
            options={
                'verbose_name': 'Промо-код',
                'verbose_name_plural': 'Промо-коды',
            },
        ),
        migrations.CreateModel(
            name='Wishlist',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('added_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Избранное',
                'verbose_name_plural': 'Избранное',
            },
        ),
    ]
