
from decimal import Decimal
import uuid
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from apps.catalog.models import ProductVariant
class PromoCode(models.Model):
    DISCOUNT_PERCENT = "percent"
    DISCOUNT_FIXED = "fixed"
    DISCOUNT_TYPE_CHOICES = [
        (DISCOUNT_PERCENT, "Процент (%)"),
        (DISCOUNT_FIXED, "Фиксированная сумма (₽)"),
    ]
    code = models.CharField("Код", max_length=50, unique=True, db_index=True)
    discount_type = models.CharField("Тип скидки", max_length=10, choices=DISCOUNT_TYPE_CHOICES)
    discount_value = models.DecimalField(
        "Размер скидки", max_digits=10, decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    valid_from = models.DateTimeField("Действует с")
    valid_to = models.DateTimeField("Действует по")
    usage_limit = models.PositiveIntegerField("Лимит использований", null=True, blank=True)
    used_count = models.PositiveIntegerField("Использований", default=0)
    min_order_amount = models.DecimalField(
        "Минимальная сумма заказа", max_digits=10, decimal_places=2,
        default=0,
    )
    is_active = models.BooleanField("Активен", default=True)
    class Meta:
        verbose_name = "Промо-код"
        verbose_name_plural = "Промо-коды"
    def __str__(self):
        return self.code
    def is_valid(self):
        from django.utils import timezone
        now = timezone.now()
        if not self.is_active:
            return False
        if now < self.valid_from or now > self.valid_to:
            return False
        if self.usage_limit and self.used_count >= self.usage_limit:
            return False
        return True
    def calculate_discount(self, total):
        if self.discount_type == self.DISCOUNT_PERCENT:
            return (total * self.discount_value / 100).quantize(total)
        return min(self.discount_value, total)
class Cart(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        null=True, blank=True,
        related_name="cart", verbose_name="Пользователь",
    )
    session_key = models.CharField("Ключ сессии", max_length=40, null=True, blank=True, db_index=True)
    promo_code = models.ForeignKey(
        PromoCode, on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name="Промо-код",
    )
    created_at = models.DateTimeField("Создана", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлена", auto_now=True)
    class Meta:
        verbose_name = "Корзина"
        verbose_name_plural = "Корзины"
    def __str__(self):
        return f"Корзина {'пользователя ' + str(self.user) if self.user else 'гостя'}"
    @property
    def total_items(self):
        return sum(item.qty for item in self.items.all())
    @property
    def subtotal(self):
        return sum(item.total_price for item in self.items.select_related("variant"))
    @property
    def discount_amount(self):
        if self.promo_code and self.promo_code.is_valid():
            return self.promo_code.calculate_discount(self.subtotal)
        return 0
    @property
    def total(self):
        return max(self.subtotal - self.discount_amount, 0)

    @property
    def savings(self):
        total = 0
        for item in self.items.select_related("variant"):
            otp = item.old_total_price
            if otp:
                total += otp - item.total_price
        return total
class CartItem(models.Model):
    cart = models.ForeignKey(
        Cart, on_delete=models.CASCADE,
        related_name="items", verbose_name="Корзина",
    )
    variant = models.ForeignKey(
        ProductVariant, on_delete=models.CASCADE,
        verbose_name="Вариант товара",
    )
    qty = models.PositiveIntegerField("Количество", default=1, validators=[MinValueValidator(1)])
    class Meta:
        verbose_name = "Позиция корзины"
        verbose_name_plural = "Позиции корзины"
        unique_together = [("cart", "variant")]
    def __str__(self):
        return f"{self.variant} × {self.qty}"
    @property
    def total_price(self):
        p = self.variant.effective_price
        return (p * self.qty) if p else Decimal("0")

    @property
    def old_total_price(self):
        old_price = self.variant.effective_old_price
        price = self.variant.effective_price
        if old_price and price and old_price > price:
            return old_price * self.qty
        return None
class Order(models.Model):
    STATUS_NEW = "new"
    STATUS_PAID = "paid"
    STATUS_ASSEMBLING = "assembling"
    STATUS_SHIPPED = "shipped"
    STATUS_DELIVERED = "delivered"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (STATUS_NEW, "Новый"),
        (STATUS_PAID, "Оплачен"),
        (STATUS_ASSEMBLING, "В сборке"),
        (STATUS_SHIPPED, "Передан в доставку"),
        (STATUS_DELIVERED, "Доставлен"),
        (STATUS_COMPLETED, "Завершён"),
        (STATUS_CANCELLED, "Отменён"),
    ]
    DELIVERY_PICKUP = "pickup"
    DELIVERY_COURIER = "courier"
    DELIVERY_CDEK_PVZ = "cdek_pvz"
    DELIVERY_CDEK_DOOR = "cdek_door"
    DELIVERY_CHOICES = [
        (DELIVERY_PICKUP, "Самовывоз"),
        (DELIVERY_COURIER, "Курьер по городу"),
        (DELIVERY_CDEK_PVZ, "СДЭК — до ПВЗ"),
        (DELIVERY_CDEK_DOOR, "СДЭК — курьером до двери"),
    ]
    PAYMENT_CARD = "card"
    PAYMENT_SBP = "sbp"
    PAYMENT_COD = "cod"
    PAYMENT_INTERNAL = "internal"
    PAYMENT_CHOICES = [
        (PAYMENT_CARD, "Банковская карта"),
        (PAYMENT_SBP, "СБП"),
        (PAYMENT_COD, "При получении"),
        (PAYMENT_INTERNAL, "Внутренний счет"),
    ]
    PAYMENT_STATUS_PENDING = "pending"
    PAYMENT_STATUS_PAID = "paid"
    PAYMENT_STATUS_REFUNDED = "refunded"
    PAYMENT_STATUS_CHOICES = [
        (PAYMENT_STATUS_PENDING, "Ожидает оплаты"),
        (PAYMENT_STATUS_PAID, "Оплачен"),
        (PAYMENT_STATUS_REFUNDED, "Возвращён"),
    ]
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="orders", verbose_name="Пользователь",
    )
    status = models.CharField(
        "Статус", max_length=20,
        choices=STATUS_CHOICES, default=STATUS_NEW, db_index=True,
    )
    delivery_type = models.CharField("Тип доставки", max_length=20, choices=DELIVERY_CHOICES)
    delivery_address = models.JSONField("Адрес доставки", default=dict)
    delivery_cost = models.DecimalField("Стоимость доставки", max_digits=10, decimal_places=2, default=0)
    cdek_track_number = models.CharField("Трек-номер СДЭК", max_length=100, blank=True)
    cdek_order_uuid = models.UUIDField("UUID заказа СДЭК", null=True, blank=True)
    cdek_pvz_code = models.CharField("Код ПВЗ СДЭК", max_length=50, blank=True)
    cdek_pvz_address = models.CharField("Адрес ПВЗ СДЭК", max_length=500, blank=True)
    payment_method = models.CharField("Способ оплаты", max_length=10, choices=PAYMENT_CHOICES)
    payment_status = models.CharField(
        "Статус оплаты", max_length=20,
        choices=PAYMENT_STATUS_CHOICES, default=PAYMENT_STATUS_PENDING,
    )
    payment_id = models.CharField("ID платежа (шлюз)", max_length=100, blank=True)
    promo_code = models.ForeignKey(
        PromoCode, on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name="Промо-код",
    )
    discount_amount = models.DecimalField("Скидка", max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField("Итог", max_digits=10, decimal_places=2)
    contact_name = models.CharField("Имя получателя", max_length=200, blank=True)
    contact_phone = models.CharField("Телефон получателя", max_length=20, blank=True)
    contact_email = models.EmailField("Email получателя", blank=True)
    comment = models.TextField("Комментарий к заказу", blank=True)
    is_organization = models.BooleanField("Заказ на организацию", default=False)
    org_name = models.CharField("Название организации", max_length=300, blank=True)
    org_inn = models.CharField("ИНН", max_length=12, blank=True)
    recipient_name = models.CharField("Имя другого получателя", max_length=200, blank=True)
    recipient_phone = models.CharField("Телефон другого получателя", max_length=20, blank=True)
    phone_code = models.CharField("Код телефона", max_length=5, default="+7")
    created_at = models.DateTimeField("Создан", auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField("Обновлён", auto_now=True)
    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["user", "created_at"]),
        ]
    def __str__(self):
        return f"Заказ #{self.pk}"

    @property
    def delivery_recipient_name(self):
        return (self.recipient_name or self.contact_name or "").strip()

    @property
    def delivery_recipient_phone(self):
        phone = (self.recipient_phone or self.contact_phone or "").strip()
        if not phone or phone.startswith("+") or not self.recipient_phone:
            return phone
        digits = "".join(ch for ch in phone if ch.isdigit())
        code = (self.phone_code or "+7").strip()
        code_digits = "".join(ch for ch in code if ch.isdigit())
        if digits.startswith(code_digits):
            return f"{code}{digits[len(code_digits):]}"
        return f"{code}{digits}"

    @property
    def has_other_recipient(self):
        return bool(self.recipient_name or self.recipient_phone)

    @property
    def items_subtotal(self):
        return sum((item.total_price for item in self.items.all()), Decimal("0"))

    @property
    def delivery_included_in_total(self):
        expected = self.items_subtotal - (self.discount_amount or Decimal("0"))
        expected += self.delivery_cost or Decimal("0")
        return self.total_amount == expected

class OrderItem(models.Model):
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE,
        related_name="items", verbose_name="Заказ",
    )
    variant = models.ForeignKey(
        ProductVariant, on_delete=models.SET_NULL,
        null=True, verbose_name="Вариант товара",
    )
    product_name = models.CharField("Название товара (снимок)", max_length=300)
    variant_description = models.CharField("Описание варианта (снимок)", max_length=200)
    qty = models.PositiveIntegerField("Количество")
    price_at_order = models.DecimalField("Цена на момент заказа", max_digits=10, decimal_places=2)
    class Meta:
        verbose_name = "Позиция заказа"
        verbose_name_plural = "Позиции заказа"
    def __str__(self):
        return f"{self.product_name} × {self.qty}"
    @property
    def total_price(self):
        # Legacy order rows may not contain a stored price or quantity.  They
        # must remain viewable in the admin rather than raising ``None * None``.
        return (self.price_at_order or Decimal("0")) * (self.qty or 0)


class RecurringOrder(models.Model):
    STATUS_PENDING = "pending"
    STATUS_ACTIVE = "active"
    STATUS_PAUSED = "paused"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Ожидает сохранения карты"),
        (STATUS_ACTIVE, "Активен"),
        (STATUS_PAUSED, "Приостановлен"),
        (STATUS_CANCELLED, "Отключён"),
    ]

    source_order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name="recurring_plan",
        verbose_name="Исходный заказ",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recurring_orders",
        verbose_name="Пользователь",
    )
    interval_weeks = models.PositiveSmallIntegerField("Интервал (недель)", default=1)
    saved_payment_method_id = models.CharField(
        "Сохранённый способ оплаты ЮKassa", max_length=100, blank=True, db_index=True,
    )
    status = models.CharField(
        "Статус", max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True,
    )
    next_charge_at = models.DateTimeField("Следующее списание", null=True, blank=True, db_index=True)
    last_charge_at = models.DateTimeField("Последнее списание", null=True, blank=True)
    last_error = models.TextField("Последняя ошибка", blank=True)
    created_at = models.DateTimeField("Создан", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлён", auto_now=True)

    class Meta:
        verbose_name = "Автоповтор заказа"
        verbose_name_plural = "Автоповторы заказов"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Автоповтор заказа #{self.source_order_id}"


class RecurringCharge(models.Model):
    STATUS_PENDING = "pending"
    STATUS_PROCESSING = "processing"
    STATUS_SUCCEEDED = "succeeded"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Ожидает"),
        (STATUS_PROCESSING, "Обрабатывается"),
        (STATUS_SUCCEEDED, "Оплачен"),
        (STATUS_FAILED, "Ошибка"),
    ]

    recurring_order = models.ForeignKey(
        RecurringOrder,
        on_delete=models.CASCADE,
        related_name="charges",
        verbose_name="Автоповтор",
    )
    scheduled_for = models.DateTimeField("Запланировано на")
    order = models.OneToOneField(
        Order,
        on_delete=models.SET_NULL,
        related_name="recurring_charge",
        verbose_name="Созданный заказ",
        null=True,
        blank=True,
    )
    idempotency_key = models.UUIDField("Ключ идемпотентности", default=uuid.uuid4, unique=True)
    status = models.CharField(
        "Статус", max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True,
    )
    error_message = models.TextField("Ошибка", blank=True)
    created_at = models.DateTimeField("Создан", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлён", auto_now=True)

    class Meta:
        verbose_name = "Списание автоповтора"
        verbose_name_plural = "Списания автоповторов"
        ordering = ["-scheduled_for"]
        constraints = [
            models.UniqueConstraint(
                fields=["recurring_order", "scheduled_for"],
                name="unique_recurring_charge_schedule",
            ),
        ]

    def __str__(self):
        return f"Списание #{self.pk} для автоповтора #{self.recurring_order_id}"
class Wishlist(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="wishlist", verbose_name="Пользователь",
    )
    product = models.ForeignKey(
        "catalog.Product", on_delete=models.CASCADE,
        verbose_name="Товар",
    )
    added_at = models.DateTimeField("Добавлено", auto_now_add=True)
    class Meta:
        verbose_name = "Избранное"
        verbose_name_plural = "Избранное"
        unique_together = [("user", "product")]
class ProductNote(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="product_notes", verbose_name="Пользователь")
    product = models.ForeignKey("catalog.Product", on_delete=models.CASCADE, related_name="user_notes", verbose_name="Товар")
    text = models.TextField("Текст заметки")
    created_at = models.DateTimeField("Создана", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлена", auto_now=True)

    class Meta:
        verbose_name = "Заметка"
        verbose_name_plural = "Заметки"
        unique_together = [("user", "product")]

class Banner(models.Model):
    from imagekit.models import ProcessedImageField
    from imagekit.processors import ResizeToFit
    title = models.CharField("Заголовок", max_length=200)
    subtitle = models.CharField("Подзаголовок", max_length=300, blank=True)
    link = models.URLField("Ссылка", blank=True)
    is_active = models.BooleanField("Активен", default=True)
    show_from = models.DateTimeField("Показывать с", null=True, blank=True)
    show_to = models.DateTimeField("Показывать по", null=True, blank=True)
    order = models.PositiveIntegerField("Порядок", default=0)
    created_at = models.DateTimeField("Создан", auto_now_add=True)
    class Meta:
        verbose_name = "Баннер"
        verbose_name_plural = "Баннеры"
        ordering = ["order"]
    def __str__(self):
        return self.title
