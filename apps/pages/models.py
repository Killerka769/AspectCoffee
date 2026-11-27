from django.core.validators import FileExtensionValidator
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


def library_upload_to(instance, filename):
    return f"library/{filename}"


def reel_video_upload_to(instance, filename):
    return f"reels/{filename}"


def reel_cover_upload_to(instance, filename):
    return f"reels/covers/{filename}"


def popup_image_upload_to(instance, filename):
    return f"popups/{filename}"


def page_banner_upload_to(instance, filename):
    return f"banners/{filename}"


class LegalDocument(models.Model):
    """Юридический документ, управляемый через админку.

    Используется для: публичной оферты, политики конфиденциальности,
    пользовательского соглашения, возврата и т.п. Содержимое можно
    редактировать через Django admin, не трогая шаблоны.
    """

    SLUG_CHOICES = [
        ("public_offer", _("Публичная оферта")),
        ("privacy", _("Политика конфиденциальности")),
        ("user_agreement", _("Пользовательское соглашение")),
        ("return_money", _("Возврат денег")),
        ("shipment_and_payment", _("Доставка и оплата")),
        ("cookies", _("Использование cookies")),
    ]

    slug = models.SlugField(
        _("Идентификатор"),
        max_length=64,
        unique=True,
        choices=SLUG_CHOICES,
        help_text=_("Уникальный ключ документа. Используется в URL."),
    )
    title = models.CharField(_("Заголовок"), max_length=200)
    meta_description = models.CharField(
        _("Meta description (SEO)"), max_length=300, blank=True,
    )
    content = models.TextField(
        _("Содержимое (HTML)"),
        help_text=_("HTML-разметка документа. Можно использовать заголовки h2-h3, списки, абзацы."),
    )
    last_updated_label = models.CharField(
        _("Подпись даты обновления"),
        max_length=80,
        blank=True,
        default="Дата последнего обновления: 1 января 2026 г.",
    )
    is_active = models.BooleanField(_("Активен"), default=True, db_index=True)
    created_at = models.DateTimeField(_("Создан"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Обновлён"), auto_now=True)

    class Meta:
        verbose_name = _("Юридический документ")
        verbose_name_plural = _("Юридические документы")
        ordering = ["slug"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse("pages:legal_document", kwargs={"slug": self.slug})


class Inquiry(models.Model):
    """Обращение с публичной формы. Пишется в базу до отправки письма."""

    class FormType(models.TextChoices):
        CONTACT = "contact", _("Контакты")
        PARTNER = "partner", _("Партнёры")
        SUBSCRIPTION = "subscription", _("Подписка")
        COFFEE_OFFICE = "coffee_office", _("Кофе в офис")

    form_type = models.CharField(
        _("Откуда"),
        max_length=20,
        choices=FormType.choices,
        db_index=True,
    )
    name = models.CharField(_("Имя"), max_length=120, blank=True, default="")
    phone = models.CharField(_("Телефон"), max_length=32, blank=True, default="")
    email = models.EmailField(_("Email"), blank=True, default="")
    message = models.TextField(_("Сообщение"))
    created_at = models.DateTimeField(_("Создана"), auto_now_add=True)
    is_processed = models.BooleanField(_("Обработана"), default=False, db_index=True)

    class Meta:
        verbose_name = _("Заявка")
        verbose_name_plural = _("Заявки")
        ordering = ["-created_at"]

    def __str__(self):
        who = self.name or self.email or self.phone or "без контакта"
        return f"{self.get_form_type_display()}: {who}"


# class Banner(models.Model):
#     """Promo banner shown on the home page (above 'Сорта недели') and other slots.
#     Configurable in Django Admin so we don't hardcode links to the original site.
#     """

#     SLOT_CHOICES = [
#         ("home_weekly", _("Главная — над «Сорта недели»")),
#         ("home_top", _("Главная — Hero (вверху)")),
#         ("home_bottom", _("Главная — внизу")),
#         ("popular_block", _("Главная — блок «Популярное» (карточки в сетке)")),
#         ("new_block", _("Главная — блок «Новое» (карточки в сетке)")),
#     ]

#     slot = models.CharField(_("Слот"), max_length=32, choices=SLOT_CHOICES, default="home_weekly")
#     title = models.CharField(_("Заголовок"), max_length=200)
#     description = models.CharField(_("Описание"), max_length=500, blank=True)
#     image = models.ImageField(_("Изображение"), upload_to="banners/", blank=True, null=True)
#     link_url = models.CharField(_("URL"), max_length=500, blank=True)
#     button_label = models.CharField(_("Текст кнопки"), max_length=80, blank=True, default="Перейти")
#     is_active = models.BooleanField(_("Активен"), default=True)
#     order = models.PositiveIntegerField(_("Порядок"), default=0)
#     created_at = models.DateTimeField(_("Создан"), auto_now_add=True)

#     class Meta:
#         verbose_name = _("Баннер")
#         verbose_name_plural = _("Баннеры")
#         ordering = ["slot", "order", "-created_at"]

#     def __str__(self):
#         return f"{self.get_slot_display()}: {self.title}"


# class SiteLink(models.Model):
#     """Configurable links shown in footer / promo blocks.
#     Replaces hardcoded shop.aspectcoffee.ru references."""

#     GROUP_CHOICES = [
#         ("footer_company", _("Футер — Компания")),
#         ("footer_help", _("Футер — Помощь")),
#         ("footer_catalog", _("Футер — Каталог")),
#         ("promo", _("Промо-блоки")),
#     ]
#     group = models.CharField(_("Группа"), max_length=32, choices=GROUP_CHOICES)
#     label = models.CharField(_("Название"), max_length=120)
#     url = models.CharField(_("URL"), max_length=500)
#     open_new_tab = models.BooleanField(_("В новой вкладке"), default=False)
#     is_active = models.BooleanField(_("Активна"), default=True)
#     order = models.PositiveIntegerField(_("Порядок"), default=0)

#     class Meta:
#         verbose_name = _("Ссылка сайта")
#         verbose_name_plural = _("Ссылки сайта")
#         ordering = ["group", "order", "label"]

#     def __str__(self):
#         return f"{self.get_group_display()}: {self.label}"


class CommunityPost(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="community_posts",
        verbose_name=_("Автор"),
    )
    title = models.CharField(_("Заголовок"), max_length=160)
    text = models.TextField(_("Текст"))
    image = models.ImageField(_("Изображение"), upload_to="community/", blank=True)
    is_published = models.BooleanField(_("Опубликовано"), default=False, db_index=True)
    created_at = models.DateTimeField(_("Создано"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Обновлено"), auto_now=True)

    class Meta:
        verbose_name = _("Запись сообщества")
        verbose_name_plural = _("Записи сообщества")
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class CommunityPostLike(models.Model):
    post = models.ForeignKey(
        CommunityPost, on_delete=models.CASCADE,
        related_name="likes", verbose_name=_("Запись"),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="community_post_likes", verbose_name=_("Пользователь"),
    )
    created_at = models.DateTimeField(_("Отмечено"), auto_now_add=True)

    class Meta:
        verbose_name = _("Отметка «нравится»")
        verbose_name_plural = _("Отметки «нравится»")
        unique_together = [("post", "user")]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user_id} -> post {self.post_id}"


# class CommunityPostDislike(models.Model):
#     post = models.ForeignKey(CommunityPost, on_delete=models.CASCADE, related_name="dislikes", verbose_name=_("Запись"))
#     user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="community_post_dislikes", verbose_name=_("Пользователь"))
#     created_at = models.DateTimeField(_("Создано"), auto_now_add=True)

#     class Meta:
#         verbose_name = _("Отметка «не нравится»")
#         verbose_name_plural = _("Отметки «не нравится»")
#         unique_together = [("post", "user")]


# class CommunityPostBookmark(models.Model):
#     post = models.ForeignKey(CommunityPost, on_delete=models.CASCADE, related_name="bookmarks", verbose_name=_("Запись"))
#     user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="community_post_bookmarks", verbose_name=_("Пользователь"))
#     created_at = models.DateTimeField(_("Создано"), auto_now_add=True)

#     class Meta:
#         verbose_name = _("Закладка сообщества")
#         verbose_name_plural = _("Закладки сообщества")
#         unique_together = [("post", "user")]


# class CommunityPostRepost(models.Model):
#     post = models.ForeignKey(CommunityPost, on_delete=models.CASCADE, related_name="reposts", verbose_name=_("Запись"))
#     user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="community_post_reposts", verbose_name=_("Пользователь"))
#     created_at = models.DateTimeField(_("Создано"), auto_now_add=True)

#     class Meta:
#         verbose_name = _("Репост сообщества")
#         verbose_name_plural = _("Репосты сообщества")
#         unique_together = [("post", "user")]


class CommunityPostComment(models.Model):
    post = models.ForeignKey(CommunityPost, on_delete=models.CASCADE, related_name="comments", verbose_name=_("Запись"))
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="community_post_comments", verbose_name=_("Пользователь"))
    parent = models.ForeignKey("self", on_delete=models.CASCADE, related_name="replies", null=True, blank=True, verbose_name=_("Ответ на комментарий"))
    text = models.TextField(_("Комментарий"), max_length=1000)
    is_approved = models.BooleanField("Одобрено", default=False, db_index=True)
    created_at = models.DateTimeField(_("Создан"), auto_now_add=True)

    class Meta:
        verbose_name = _("Комментарий сообщества")
        verbose_name_plural = _("Комментарии сообщества")
        ordering = ["created_at"]


class MediaFile(models.Model):
    """Файл медиатеки. Ссылку копируют и вставляют в редактор статей."""

    IMAGE_EXTENSIONS = ("jpg", "jpeg", "png", "gif", "webp")

    title = models.CharField(_("Название"), max_length=200)
    file = models.FileField(
        _("Файл"),
        upload_to=library_upload_to,
        validators=[
            FileExtensionValidator(
                allowed_extensions=[*IMAGE_EXTENSIONS, "pdf"],
            ),
        ],
        help_text=_("Картинка (jpg, png, webp, gif) или PDF. Файл попадает в media/library/."),
    )
    created_at = models.DateTimeField(_("Загружен"), auto_now_add=True)

    class Meta:
        verbose_name = _("Файл медиатеки")
        verbose_name_plural = _("Медиатека")
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    @property
    def is_image(self):
        name = (self.file.name or "").lower()
        return name.endswith(tuple(f".{ext}" for ext in self.IMAGE_EXTENSIONS))


class Reel(models.Model):
    """Короткое вертикальное видео. Загружается из админки и показывается на главной."""

    title = models.CharField(_("Заголовок"), max_length=200)
    video = models.FileField(
        _("Видео"),
        upload_to=reel_video_upload_to,
        validators=[
            FileExtensionValidator(
                allowed_extensions=["mp4", "webm"],
                message=_("Можно загрузить только MP4 или WebM."),
            ),
        ],
        help_text=_("Только mp4 или webm. Файл попадает в media/reels/."),
    )
    cover = models.ImageField(
        _("Обложка"),
        upload_to=reel_cover_upload_to,
        blank=True,
        validators=[
            FileExtensionValidator(
                allowed_extensions=["jpg", "jpeg", "png", "webp", "gif"],
            ),
        ],
        help_text=_("Необязательное превью, пока видео не запущено."),
    )
    is_active = models.BooleanField(_("На сайте"), default=True, db_index=True)
    order = models.PositiveIntegerField(_("Порядок"), default=0)

    class Meta:
        verbose_name = _("Шортс")
        verbose_name_plural = _("Шортсы")
        ordering = ["order", "id"]

    def __str__(self):
        return self.title

    @property
    def video_content_type(self):
        name = (self.video.name or "").lower()
        if name.endswith(".webm"):
            return "video/webm"
        return "video/mp4"


class PopupMessage(models.Model):
    """Мотивационное окно. На сайте рисуется только активное и подходящее к странице."""

    class ShowOn(models.TextChoices):
        HOME = "home", _("Главная")
        CATALOG = "catalog", _("Каталог")
        ALL = "all", _("Все страницы")

    class Placement(models.TextChoices):
        SCREEN = "screen", _("На весь экран")
        EDGE = "edge", _("На странице")

    class Side(models.TextChoices):
        RIGHT = "right", _("Справа")
        LEFT = "left", _("Слева")
        TOP = "top", _("Сверху")
        BOTTOM = "bottom", _("Снизу")

    title = models.CharField(_("Заголовок"), max_length=200)
    text = models.TextField(_("Текст сообщения"))
    button_text = models.CharField(_("Текст кнопки"), max_length=80, blank=True)
    button_link = models.URLField(_("Ссылка кнопки"), blank=True)
    image = models.ImageField(
        _("Картинка"),
        upload_to=popup_image_upload_to,
        blank=True,
        validators=[
            FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png", "webp", "gif"]),
        ],
    )
    delay_seconds = models.PositiveIntegerField(_("Показать через, сек"), default=5)
    is_active = models.BooleanField(_("Включено"), default=True, db_index=True)
    show_on_pages = models.CharField(
        _("Где показывать"),
        max_length=16,
        choices=ShowOn.choices,
        default=ShowOn.ALL,
    )
    placement = models.CharField(
        _("Как показывать"),
        max_length=16,
        choices=Placement.choices,
        default=Placement.SCREEN,
    )
    side = models.CharField(
        _("Сторона"),
        max_length=16,
        choices=Side.choices,
        default=Side.RIGHT,
        help_text=_("Используется, когда окно показывается на странице, а не на весь экран."),
    )
    created_at = models.DateTimeField(_("Создано"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Обновлено"), auto_now=True)

    class Meta:
        verbose_name = _("Всплывающее окно")
        verbose_name_plural = _("Всплывающие окна")
        ordering = ["-updated_at"]

    def __str__(self):
        return self.title


class PageBanner(models.Model):
    """Баннер карусели. На странице выводятся только активные слайды выбранного раздела."""

    class Page(models.TextChoices):
        HOME = "home", _("Главная")
        CATALOG = "catalog", _("Каталог")
        JOURNAL = "journal", _("Журнал")

    title = models.CharField(_("Название"), max_length=200)
    image = models.ImageField(
        _("Изображение"),
        upload_to=page_banner_upload_to,
        validators=[
            FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png", "webp", "gif"]),
        ],
    )
    link = models.URLField(_("Ссылка"), blank=True)
    page = models.CharField(
        _("Страница"),
        max_length=16,
        choices=Page.choices,
        default=Page.HOME,
        db_index=True,
    )
    order = models.IntegerField(_("Порядок"), default=0)
    is_active = models.BooleanField(_("На сайте"), default=True, db_index=True)

    class Meta:
        verbose_name = _("Баннер")
        verbose_name_plural = _("Баннеры-слайдеры")
        ordering = ["order", "id"]

    def __str__(self):
        return self.title


class ReviewComment(models.Model):
    review = models.ForeignKey("catalog.Review", on_delete=models.CASCADE, related_name="public_comments", verbose_name=_("Отзыв"))
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="review_comments", verbose_name=_("Пользователь"))
    parent = models.ForeignKey("self", on_delete=models.CASCADE, related_name="replies", null=True, blank=True, verbose_name=_("Ответ на комментарий"))
    text = models.TextField(_("Комментарий"), max_length=1000)
    is_approved = models.BooleanField("Одобрено", default=False, db_index=True)
    created_at = models.DateTimeField(_("Создан"), auto_now_add=True)

    class Meta:
        verbose_name = _("Комментарий к отзыву")
        verbose_name_plural = _("Комментарии к отзывам")
        ordering = ["created_at"]
