
from django.db import models
from django.conf import settings


class Payment(models.Model):
    STATUS_PENDING = "pending"
    STATUS_SUCCEEDED = "succeeded"
    STATUS_CANCELLED = "cancelled"
    STATUS_REFUNDED = "refunded"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Ожидает оплаты"),
        (STATUS_SUCCEEDED, "Оплачен"),
        (STATUS_CANCELLED, "Отменён"),
        (STATUS_REFUNDED, "Возвращён"),
    ]

    order = models.OneToOneField(
        "orders.Order",
        on_delete=models.CASCADE,
        related_name="payment",
        verbose_name="Заказ",
    )
    yookassa_id = models.CharField(
        "ID платежа (ЮKassa)", max_length=100,
        unique=True, db_index=True, blank=True,
    )
    yookassa_refund_id = models.CharField(
        "ID возврата (ЮKassa)", max_length=100, blank=True,
    )
    amount = models.DecimalField("Сумма", max_digits=12, decimal_places=2)
    status = models.CharField(
        "Статус", max_length=20,
        choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True,
    )
    confirmation_url = models.URLField("URL подтверждения", blank=True)
    saved_payment_method_id = models.CharField(
        "Сохранённый способ оплаты ЮKassa", max_length=100, blank=True, db_index=True,
    )
    payment_method_saved = models.BooleanField("Способ оплаты сохранён", default=False)
    payment_method_type = models.CharField("Тип способа оплаты", max_length=32, blank=True)
    card_last4 = models.CharField("Последние 4 цифры карты", max_length=4, blank=True)
    created_at = models.DateTimeField("Создан", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлён", auto_now=True)

    class Meta:
        verbose_name = "Платёж"
        verbose_name_plural = "Платежи"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Платёж #{self.pk} — заказ #{self.order_id} ({self.get_status_display()})"
