from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


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
    is_published = models.BooleanField(_("Опубликовано"), default=True)
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
