import re

from django.contrib.auth.models import AbstractUser
from django.contrib.auth.base_user import BaseUserManager
from django.core.validators import RegexValidator
from django.db import models
from imagekit.models import ProcessedImageField
from imagekit.processors import ResizeToFill
class UserManager(BaseUserManager):
    use_in_migrations = True
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email обязателен")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Суперпользователь должен иметь is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Суперпользователь должен иметь is_superuser=True.")
        return self.create_user(email, password, **extra_fields)
from django.core.exceptions import ValidationError

def validate_avatar_file(value):
    ext = value.name.split('.')[-1].lower()
    if ext not in ['jpg', 'jpeg', 'png', 'webp']:
        raise ValidationError("Неподдерживаемый формат изображения. Используйте JPG, PNG или WEBP.")
    if value.size > 2 * 1024 * 1024:
        raise ValidationError("Файл слишком велик. Максимум 2 МБ.")

class User(AbstractUser):
    ROLE_CUSTOMER = "customer"
    ROLE_WHOLESALE = "wholesale_customer"
    ROLE_WAREHOUSE = "warehouse_operator"
    ROLE_CHOICES = [
        (ROLE_CUSTOMER, "Розничный покупатель"),
        (ROLE_WHOLESALE, "Оптовый покупатель"),
        (ROLE_WAREHOUSE, "Оператор склада"),
    ]

    username = None
    email = models.EmailField("Email", unique=True)
    phone = models.CharField(
        "Телефон", max_length=20, blank=True,
        validators=[RegexValidator(r"^\+?[\d\s\-\(\)]{7,20}$", "Введите корректный номер телефона")],
    )
    phone_confirmed = models.BooleanField(
        "Телефон подтверждён",
        default=False,
        help_text="Телефон получен от OAuth-провайдера или повторно подтверждён пользователем.",
    )
    avatar = ProcessedImageField(
        upload_to="avatars/",
        processors=[ResizeToFill(200, 200)],
        format="WEBP",
        options={"quality": 80},
        blank=True, null=True,
        verbose_name="Аватар",
        validators=[validate_avatar_file],
    )
    role = models.CharField(
        "Роль", max_length=25,
        choices=ROLE_CHOICES, default=ROLE_CUSTOMER, db_index=True,
    )
    bonus_points = models.PositiveIntegerField("Бонусные баллы", default=0)
    balance = models.DecimalField(
        "Внутренний баланс (₽)", max_digits=12, decimal_places=2,
        default=0, help_text="Пополняемый баланс для оплаты заказов",
    )
    email_confirmed = models.BooleanField("Email подтверждён", default=False)
    wholesale_discount = models.PositiveIntegerField(
        "Оптовая скидка (%)", default=0,
        help_text="Скидка от розничной цены для оптового покупателя",
    )
    credit_limit = models.DecimalField(
        "Лимит кредита", max_digits=12, decimal_places=2,
        null=True, blank=True,
    )
    company_name = models.CharField("Компания", max_length=255, blank=True)
    company_inn = models.CharField("ИНН", max_length=12, blank=True)
    company_kpp = models.CharField("КПП", max_length=9, blank=True)
    company_address = models.CharField("Юридический адрес", max_length=500, blank=True)
    company_bank_account = models.CharField("Расчётный счёт", max_length=25, blank=True)
    telegram = models.CharField("Telegram", max_length=255, blank=True, help_text="Username или ссылка")
    viber = models.CharField("Viber", max_length=255, blank=True, help_text="Номер или ссылка")
    telegram_id = models.CharField("Telegram ID", max_length=100, blank=True, help_text="Числовой ID для уведомлений")
    viber_id = models.CharField("Viber ID", max_length=100, blank=True, help_text="Числовой ID для уведомлений")

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    objects = UserManager()

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
        constraints = [
            models.UniqueConstraint(
                fields=["phone"],
                condition=~models.Q(phone=""),
                name="users_unique_nonempty_phone",
            ),
        ]

    def __str__(self):
        return self.email

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.email

    def get_level(self):
        """Community level derived from the user's real activity."""
        posts = self.community_posts.count() if hasattr(self, "community_posts") else 0
        comments = self.community_post_comments.count() if hasattr(self, "community_post_comments") else 0
        orders = self.orders.count() if hasattr(self, "orders") else 0
        score = posts * 5 + comments + orders * 2
        if score >= 100:
            return {"name": "Эксперт", "color": "#8b42c7"}
        if score >= 40:
            return {"name": "Продвинутый", "color": "#1f75d6"}
        if score >= 10:
            return {"name": "Любитель", "color": "#248354"}
        return {"name": "Новичок", "color": "#999999"}

    def get_city(self):
        address = self.addresses.order_by("-is_default", "id").first()
        return address.city if address else ""

    @property
    def is_wholesale(self):
        return self.role == self.ROLE_WHOLESALE

    @property
    def is_warehouse_operator(self):
        return self.role == self.ROLE_WAREHOUSE
    @property
    def phone_display(self):
        """Format phone as international: +7 901 357-35-77"""
        if not self.phone:
            return ""
        raw = re.sub(r"[^0-9+]", "", self.phone)
        if not raw.startswith("+"):
            raw = "+" + raw
        try:
            import phonenumbers
            parsed = phonenumbers.parse(raw, None)
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
        except Exception:
            return self.phone


    def get_available_bonus_points(self):
        from django.utils import timezone
        from datetime import timedelta
        now = timezone.now()
        earned = self.bonus_transactions.filter(
            type=BonusTransaction.TYPE_EARN,
            expires_at__gt=now,
        ).aggregate(t=models.Sum("amount"))["t"] or 0
        spent = self.bonus_transactions.filter(
            type=BonusTransaction.TYPE_SPEND,
        ).aggregate(t=models.Sum("amount"))["t"] or 0
        expired = self.bonus_transactions.filter(
            type=BonusTransaction.TYPE_EXPIRE,
        ).aggregate(t=models.Sum("amount"))["t"] or 0
        return max(earned - spent - expired, 0)

    def earn_bonus(self, points, order=None, description=""):
        from django.utils import timezone
        from datetime import timedelta
        BonusTransaction.objects.create(
            user=self,
            type=BonusTransaction.TYPE_EARN,
            amount=points,
            order=order,
            description=description or f"Начисление за заказ #{order.pk}" if order else description,
            expires_at=timezone.now() + timedelta(days=180),
        )
        self.bonus_points = self.get_available_bonus_points()
        self.save(update_fields=["bonus_points"])

    def spend_bonus(self, points, order=None, description=""):
        available = self.get_available_bonus_points()
        if points > available:
            points = available
        if points <= 0:
            return 0
        BonusTransaction.objects.create(
            user=self,
            type=BonusTransaction.TYPE_SPEND,
            amount=points,
            order=order,
            description=description or f"Оплата баллами заказа #{order.pk}" if order else description,
        )
        self.bonus_points = self.get_available_bonus_points()
        self.save(update_fields=["bonus_points"])
        return points

    def expire_old_bonus(self):
        from django.utils import timezone
        now = timezone.now()
        expired_txns = BonusTransaction.objects.filter(
            user=self,
            type=BonusTransaction.TYPE_EARN,
            expires_at__lte=now,
        )
        for txn in expired_txns:
            already_expired = BonusTransaction.objects.filter(
                user=self,
                type=BonusTransaction.TYPE_EXPIRE,
                description__contains=f"#{txn.pk}",
            ).exists()
            if not already_expired:
                BonusTransaction.objects.create(
                    user=self,
                    type=BonusTransaction.TYPE_EXPIRE,
                    amount=txn.amount,
                    description=f"Сгорание баллов (транзакция #{txn.pk})",
                )
        self.bonus_points = self.get_available_bonus_points()
        self.save(update_fields=["bonus_points"])

    def save(self, *args, **kwargs):
        if self.role == self.ROLE_WAREHOUSE:
            self.is_staff = True
        super().save(*args, **kwargs)
class Address(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name="addresses", verbose_name="Пользователь",
    )
    label = models.CharField("Метка", max_length=100, blank=True, help_text="Например: «Дом», «Работа»")
    city = models.CharField("Город", max_length=200)
    street = models.CharField("Улица", max_length=300)
    house = models.CharField("Дом", max_length=50, blank=True)
    apartment = models.CharField("Квартира/офис", max_length=50, blank=True)
    postal_code = models.CharField("Индекс", max_length=10, blank=True)
    is_default = models.BooleanField("По умолчанию", default=False)
    class Meta:
        verbose_name = "Адрес"
        verbose_name_plural = "Адреса"
        ordering = ["-is_default", "label"]
    def __str__(self):
        house_part = f", д. {self.house}" if self.house else ""
        return f"{self.city}, {self.street}{house_part} ({self.user.email})"
    def save(self, *args, **kwargs):
        if self.is_default:
            Address.objects.filter(user=self.user, is_default=True).update(is_default=False)
        super().save(*args, **kwargs)

class Achievement(models.Model):
    CONDITION_TYPES = [
        ("orders_count", "Количество заказов"),
        ("total_spent", "Общая сумма покупок"),
    ]
    title = models.CharField("Название", max_length=100)
    description = models.TextField("Описание", blank=True)
    icon = models.ImageField("Иконка", upload_to="achievements/", blank=True, null=True)
    condition_type = models.CharField("Тип условия", max_length=30, choices=CONDITION_TYPES)
    condition_value = models.PositiveIntegerField("Значение условия", default=0)
    sort_order = models.PositiveIntegerField("Порядок", default=0)
    is_active = models.BooleanField("Активно", default=True)
    created_at = models.DateTimeField("Создано", auto_now_add=True)

    class Meta:
        verbose_name = "Достижение"
        verbose_name_plural = "Достижения"
        ordering = ["sort_order", "pk"]

    def __str__(self):
        return self.title

    def check_user(self, user):
        from django.db.models import Sum
        from apps.orders.models import Order
        qs = Order.objects.filter(user=user).exclude(status=Order.STATUS_CANCELLED)
        if self.condition_type == "orders_count":
            return qs.count()
        elif self.condition_type == "total_spent":
            return qs.aggregate(t=Sum("total_amount"))["t"] or 0
        return 0


class DiscountLevel(models.Model):
    min_amount = models.PositiveIntegerField("Минимальная сумма покупок", default=0)
    discount_percent = models.PositiveIntegerField("Процент скидки", default=0)
    sort_order = models.PositiveIntegerField("Порядок", default=0)
    is_active = models.BooleanField("Активно", default=True)

    class Meta:
        verbose_name = "Уровень скидки"
        verbose_name_plural = "Уровни скидок"
        ordering = ["sort_order", "min_amount"]

    def __str__(self):
        return f"От {self.min_amount} ₽ — {self.discount_percent}%"


class UserAchievement(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_achievements", verbose_name="Пользователь")
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE, related_name="user_achievements", verbose_name="Достижение")
    earned_at = models.DateTimeField("Получено", auto_now_add=True)

    class Meta:
        verbose_name = "Достижение пользователя"
        verbose_name_plural = "Достижения пользователей"
        unique_together = ["user", "achievement"]
        ordering = ["-earned_at"]

    def __str__(self):
        return f"{self.user.email} — {self.achievement.title}"


class BonusTransaction(models.Model):
    TYPE_EARN = "earn"
    TYPE_SPEND = "spend"
    TYPE_EXPIRE = "expire"
    TYPE_ADJUST = "adjust"
    TYPE_CHOICES = [
        (TYPE_EARN, "Начисление"),
        (TYPE_SPEND, "Списание"),
        (TYPE_EXPIRE, "Сгорание"),
        (TYPE_ADJUST, "Корректировка"),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bonus_transactions", verbose_name="Пользователь")
    type = models.CharField("Тип", max_length=10, choices=TYPE_CHOICES)
    amount = models.IntegerField("Количество баллов")
    order = models.ForeignKey("orders.Order", on_delete=models.SET_NULL, null=True, blank=True, related_name="bonus_transactions", verbose_name="Заказ")
    description = models.CharField("Описание", max_length=255, blank=True)
    created_at = models.DateTimeField("Дата", auto_now_add=True)
    expires_at = models.DateTimeField("Сгорает", null=True, blank=True)

    class Meta:
        verbose_name = "Транзакция баллов"
        verbose_name_plural = "Транзакции баллов"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email}: {self.get_type_display()} {self.amount} б."


class EmailLog(models.Model):
    recipient = models.EmailField("Получатель")
    subject = models.CharField("Тема", max_length=255)
    body = models.TextField("Содержимое")
    sent_at = models.DateTimeField("Отправлено", auto_now_add=True)
    success = models.BooleanField("Успешно", default=True)
    error_message = models.TextField("Ошибка", blank=True)

    class Meta:
        verbose_name = "Лог email"
        verbose_name_plural = "Логи email"
        ordering = ["-sent_at"]

    def __str__(self):
        return f"{self.subject} -> {self.recipient}"


class UserNotification(models.Model):
    KIND_INFO = "info"
    KIND_REPLY = "reply"
    KIND_ORDER = "order"
    KIND_ERROR = "error"
    KIND_CHOICES = [
        (KIND_INFO, "Информация"),
        (KIND_REPLY, "Ответ"),
        (KIND_ORDER, "Заказ"),
        (KIND_ERROR, "Ошибка"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name="Получатель",
    )
    actor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name="triggered_notifications",
        null=True,
        blank=True,
        verbose_name="Отправитель",
    )
    email_log = models.OneToOneField(
        EmailLog,
        on_delete=models.SET_NULL,
        related_name="user_notification",
        null=True,
        blank=True,
        verbose_name="Лог email",
    )
    title = models.CharField("Заголовок", max_length=255)
    body = models.TextField("Текст", blank=True)
    url = models.CharField("Ссылка", max_length=500, blank=True)
    kind = models.CharField("Тип", max_length=20, choices=KIND_CHOICES, default=KIND_INFO)
    is_read = models.BooleanField("Прочитано", default=False)
    created_at = models.DateTimeField("Создано", auto_now_add=True)

    class Meta:
        verbose_name = "Уведомление пользователя"
        verbose_name_plural = "Уведомления пользователей"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_read", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.user}: {self.title}"


class PushSubscription(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="push_subscriptions",
        verbose_name="Пользователь",
    )
    endpoint = models.TextField("Endpoint", unique=True)
    p256dh = models.TextField("P-256 key")
    auth = models.TextField("Auth key")
    user_agent = models.CharField("Устройство", max_length=500, blank=True)
    is_active = models.BooleanField("Активна", default=True)
    created_at = models.DateTimeField("Создана", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлена", auto_now=True)

    class Meta:
        verbose_name = "Push-подписка"
        verbose_name_plural = "Push-подписки"
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.user} — {self.endpoint[:50]}"


class PaymentTransaction(models.Model):
    """Track ЮKassa payment transactions for balance top-up."""

    STATUS_CHOICES = [
        ('pending', 'Ожидание'),
        ('completed', 'Завершено'),
        ('canceled', 'Отменено'),
        ('failed', 'Ошибка'),
    ]

    PROVIDER_CHOICES = [
        ('yookassa', 'ЮKassa'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='payment_transactions',
        verbose_name='Пользователь'
    )
    payment_id = models.CharField(
        'ID платежа',
        max_length=100,
        unique=True,
        db_index=True
    )
    amount = models.DecimalField(
        'Сумма (₽)',
        max_digits=12,
        decimal_places=2
    )
    status = models.CharField(
        'Статус',
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True
    )
    provider = models.CharField(
        'Провайдер',
        max_length=20,
        choices=PROVIDER_CHOICES,
        default='yookassa'
    )
    created_at = models.DateTimeField(
        'Создано',
        auto_now_add=True,
        db_index=True
    )
    updated_at = models.DateTimeField(
        'Обновлено',
        auto_now=True
    )
    completed_at = models.DateTimeField(
        'Завершено',
        null=True,
        blank=True
    )
    error_message = models.TextField(
        'Сообщение об ошибке',
        blank=True
    )

    class Meta:
        verbose_name = 'Платёж'
        verbose_name_plural = 'Платежи'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['status', '-created_at']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.amount} RUB ({self.status})"

    def mark_completed(self):
        """Mark payment as completed and update user balance."""
        if self.status == 'completed':
            return False

        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save()

        # Update user balance
        self.user.balance += self.amount
        self.user.save()

        return True
