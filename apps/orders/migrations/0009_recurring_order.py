import django.db.models.deletion
import uuid

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0008_alter_order_payment_method"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="RecurringOrder",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("interval_weeks", models.PositiveSmallIntegerField(default=1, verbose_name="Интервал (недель)")),
                ("saved_payment_method_id", models.CharField(blank=True, db_index=True, max_length=100, verbose_name="Сохранённый способ оплаты ЮKassa")),
                ("status", models.CharField(choices=[("pending", "Ожидает сохранения карты"), ("active", "Активен"), ("paused", "Приостановлен"), ("cancelled", "Отключён")], db_index=True, default="pending", max_length=16, verbose_name="Статус")),
                ("next_charge_at", models.DateTimeField(blank=True, db_index=True, null=True, verbose_name="Следующее списание")),
                ("last_charge_at", models.DateTimeField(blank=True, null=True, verbose_name="Последнее списание")),
                ("last_error", models.TextField(blank=True, verbose_name="Последняя ошибка")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Создан")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Обновлён")),
                ("source_order", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="recurring_plan", to="orders.order", verbose_name="Исходный заказ")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="recurring_orders", to=settings.AUTH_USER_MODEL, verbose_name="Пользователь")),
            ],
            options={"verbose_name": "Автоповтор заказа", "verbose_name_plural": "Автоповторы заказов", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="RecurringCharge",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("scheduled_for", models.DateTimeField(verbose_name="Запланировано на")),
                ("idempotency_key", models.UUIDField(default=uuid.uuid4, unique=True, verbose_name="Ключ идемпотентности")),
                ("status", models.CharField(choices=[("pending", "Ожидает"), ("processing", "Обрабатывается"), ("succeeded", "Оплачен"), ("failed", "Ошибка")], db_index=True, default="pending", max_length=16, verbose_name="Статус")),
                ("error_message", models.TextField(blank=True, verbose_name="Ошибка")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Создан")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Обновлён")),
                ("order", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="recurring_charge", to="orders.order", verbose_name="Созданный заказ")),
                ("recurring_order", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="charges", to="orders.recurringorder", verbose_name="Автоповтор")),
            ],
            options={"verbose_name": "Списание автоповтора", "verbose_name_plural": "Списания автоповторов", "ordering": ["-scheduled_for"]},
        ),
        migrations.AddConstraint(
            model_name="recurringcharge",
            constraint=models.UniqueConstraint(fields=("recurring_order", "scheduled_for"), name="unique_recurring_charge_schedule"),
        ),
    ]
