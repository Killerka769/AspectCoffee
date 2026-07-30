
from django.db import models


class StockItem(models.Model):
    """
    Warehouse stock tracking for product variants.
    Low-stock alerts are triggered via post_save signal in signals.py.
    """
    variant = models.OneToOneField(
        "catalog.ProductVariant",
        on_delete=models.CASCADE,
        related_name="stock",
        verbose_name="Вариант товара",
    )
    qty = models.PositiveIntegerField("Текущий остаток", default=0)
    min_qty = models.PositiveIntegerField(
        "Минимальный остаток", default=5,
        help_text="При падении ниже этого значения — алерт администратору",
    )
    updated_at = models.DateTimeField("Обновлён", auto_now=True)
    last_low_stock_notification = models.DateTimeField("Последнее уведомление", null=True, blank=True)


    class Meta:
        verbose_name = "Остаток на складе"
        verbose_name_plural = "Остатки на складе"

    def __str__(self):
        return f"{self.variant} — {self.qty} шт."

    @property
    def is_low(self):
        return self.qty < self.min_qty
