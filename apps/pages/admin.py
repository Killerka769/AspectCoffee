from django.contrib import admin
from django.db.models import Count, Q
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline
from .models import (
    CommunityPost, CommunityPostComment,
    CommunityPostLike, Inquiry, MediaFile, PageBanner, PopupMessage, Reel, ReviewComment, LegalDocument,
)


@admin.register(Inquiry)
class InquiryAdmin(ModelAdmin):
    list_display = ("created_at", "form_type", "name", "phone", "email", "is_processed")
    list_filter = ("form_type", "is_processed", "created_at")
    search_fields = ("name", "phone", "email", "message")
    readonly_fields = ("created_at",)
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    actions = ("mark_processed",)
    fieldsets = (
        ("Откуда", {"fields": ("form_type", "created_at", "is_processed")}),
        ("Контакты", {"fields": ("name", "phone", "email")}),
        ("Сообщение", {"fields": ("message",)}),
    )

    @admin.action(description="Отметить как обработанные")
    def mark_processed(self, request, queryset):
        updated = queryset.update(is_processed=True)
        self.message_user(request, f"Отмечено обработанными: {updated}")


@admin.register(MediaFile)
class MediaFileAdmin(ModelAdmin):
    list_display = ("preview", "title", "copy_link", "created_at")
    list_display_links = ("title",)
    search_fields = ("title", "file")
    readonly_fields = ("created_at", "preview", "copy_link")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    fieldsets = (
        (None, {
            "fields": ("title", "file", "preview", "copy_link", "created_at"),
            "description": "После сохранения скопируйте ссылку и вставьте её в редактор статей: кнопка «Изображение» → вкладка с адресом.",
        }),
    )

    @admin.display(description="Превью")
    def preview(self, obj):
        if not obj or not obj.file or not obj.is_image:
            return "—"
        return format_html(
            '<img src="{}" alt="" style="height:48px;width:72px;object-fit:cover;border-radius:4px;">',
            obj.file.url,
        )

    @admin.display(description="Ссылка")
    def copy_link(self, obj):
        if not obj or not obj.file:
            return "Ссылка появится после сохранения"
        return format_html(
            '<input type="text" readonly value="{}" onclick="this.select()" '
            'style="width:min(420px,100%);font:12px/1.4 sans-serif;">',
            obj.file.url,
        )


@admin.register(PageBanner)
class PageBannerAdmin(ModelAdmin):
    list_display = ("preview", "title", "page", "order", "is_active")
    list_display_links = ("title",)
    list_editable = ("order", "is_active")
    list_filter = ("page", "is_active")
    search_fields = ("title", "link")
    readonly_fields = ("preview",)
    ordering = ("order", "id")
    fieldsets = (
        (None, {
            "fields": ("title", "image", "preview", "link", "page", "order", "is_active"),
            "description": "Главная — страница /. Каталог — /catalog/. Журнал — /blog/ и разделы журнала.",
        }),
    )

    @admin.display(description="Превью")
    def preview(self, obj):
        if not obj or not obj.image:
            return "—"
        return format_html(
            '<img src="{}" alt="" style="height:48px;width:96px;object-fit:cover;border-radius:4px;">',
            obj.image.url,
        )


@admin.register(PopupMessage)
class PopupMessageAdmin(ModelAdmin):
    list_display = ("preview", "title", "placement", "side", "show_on_pages", "delay_seconds", "is_active", "updated_at")
    list_display_links = ("title",)
    list_editable = ("is_active",)
    list_filter = ("is_active", "show_on_pages", "placement", "side")
    search_fields = ("title", "text", "button_text")
    readonly_fields = ("preview", "created_at", "updated_at")
    ordering = ("-updated_at",)
    fieldsets = (
        (None, {"fields": ("title", "text", "is_active", "show_on_pages", "delay_seconds")}),
        ("Вид", {
            "fields": ("placement", "side"),
            "description": (
                "«На весь экран» закрывает страницу карточкой по центру. "
                "«На странице» выезжает с выбранной стороны, сайт можно листать дальше."
            ),
        }),
        ("Кнопка", {"fields": ("button_text", "button_link")}),
        ("Картинка", {"fields": ("image", "preview")}),
        ("Даты", {"fields": ("created_at", "updated_at")}),
    )

    @admin.display(description="Превью")
    def preview(self, obj):
        if not obj or not obj.image:
            return "—"
        return format_html(
            '<img src="{}" alt="" style="height:56px;width:56px;object-fit:cover;border-radius:8px;">',
            obj.image.url,
        )


@admin.register(Reel)
class ReelAdmin(ModelAdmin):
    list_display = ("preview", "title", "is_active", "order")
    list_display_links = ("title",)
    list_editable = ("is_active", "order")
    list_filter = ("is_active",)
    search_fields = ("title",)
    readonly_fields = ("preview", "player")
    ordering = ("order", "id")
    fieldsets = (
        (None, {
            "fields": ("title", "video", "cover", "is_active", "order", "player"),
            "description": "На сайте показываются только включённые ролики. Принимаются mp4 и webm.",
        }),
    )

    @admin.display(description="Превью")
    def preview(self, obj):
        if not obj or not obj.pk:
            return "—"
        if obj.cover:
            return format_html(
                '<img src="{}" alt="" style="height:72px;width:40px;object-fit:cover;border-radius:4px;background:#111;">',
                obj.cover.url,
            )
        if obj.video:
            return format_html(
                '<video src="{}" muted preload="metadata" style="height:72px;width:40px;object-fit:cover;border-radius:4px;background:#111;"></video>',
                obj.video.url,
            )
        return "—"

    @admin.display(description="Просмотр")
    def player(self, obj):
        if not obj or not obj.video:
            return "Видео появится после сохранения"
        if obj.cover:
            return format_html(
                '<video src="{}" poster="{}" controls playsinline preload="metadata" style="width:180px;max-height:320px;background:#000;"></video>',
                obj.video.url,
                obj.cover.url,
            )
        return format_html(
            '<video src="{}" controls playsinline preload="metadata" style="width:180px;max-height:320px;background:#000;"></video>',
            obj.video.url,
        )


@admin.register(LegalDocument)
class LegalDocumentAdmin(ModelAdmin):
    list_display = ("title", "slug", "is_active", "updated_at")
    list_filter = ("is_active", "slug")
    list_editable = ("is_active",)
    search_fields = ("title", "content", "slug")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("title", "slug", "is_active")}),
        ("SEO", {"fields": ("meta_description",)}),
        ("Содержимое", {
            "fields": ("last_updated_label", "content"),
            "description": "Разрешён HTML: <h2>, <h3>, <p>, <ul>, <ol>, <li>, <strong>, <em>, <a>, <br>.",
        }),
        ("Метаданные", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def save_model(self, request, obj, form, change):
        if not obj.slug:
            from django.utils.text import slugify
            obj.slug = slugify(obj.title, allow_unicode=True)
        super().save_model(request, obj, form, change)


class CommunityPostLikeInline(TabularInline):
    model = CommunityPostLike
    extra = 0
    fields = ("user", "created_at")
    readonly_fields = fields
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class CommunityPostCommentInline(TabularInline):
    model = CommunityPostComment
    extra = 0
    fields = ("user", "parent", "text", "is_approved", "created_at")
    readonly_fields = ("created_at",)


class PublishedStatusFilter(admin.SimpleListFilter):
    title = "Статус"
    parameter_name = "publication"
    field_name = "is_published"

    def lookups(self, request, model_admin):
        return (("yes", "Опубликовано"), ("no", "На модерации"))

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.filter(**{self.field_name: True})
        if self.value() == "no":
            return queryset.filter(**{self.field_name: False})
        return queryset


class ApprovedStatusFilter(PublishedStatusFilter):
    parameter_name = "approval"
    field_name = "is_approved"


@admin.register(CommunityPost)
class CommunityPostAdmin(ModelAdmin):
    list_display = ("title", "user", "likes_total", "comments_total", "is_published", "created_at")
    list_filter = (PublishedStatusFilter, "created_at")
    list_editable = ("is_published",)
    actions = ("publish_selected", "hide_selected")
    search_fields = ("title", "text", "user__email", "user__username")
    readonly_fields = ("created_at", "updated_at")
    inlines = (CommunityPostLikeInline, CommunityPostCommentInline)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _likes_total=Count("likes", distinct=True),
            _comments_total=Count("comments", filter=Q(comments__is_approved=True), distinct=True),
        )

    @admin.display(description="Лайки", ordering="_likes_total")
    def likes_total(self, obj):
        return obj._likes_total

    @admin.display(description="Комментарии", ordering="_comments_total")
    def comments_total(self, obj):
        return obj._comments_total

    @admin.action(description="Опубликовать выбранные записи")
    def publish_selected(self, request, queryset):
        updated = queryset.filter(is_published=False).update(is_published=True)
        self.message_user(request, f"Опубликовано записей: {updated}")

    @admin.action(description="Снять выбранные записи с публикации")
    def hide_selected(self, request, queryset):
        updated = queryset.filter(is_published=True).update(is_published=False)
        self.message_user(request, f"Снято с публикации записей: {updated}")


class CommentModerationAdminMixin:
    actions = ("approve_selected", "hide_selected")

    def _notify_approved(self, comment):
        from apps.users.models import UserNotification
        from apps.users.notifications import create_notification

        if isinstance(comment, CommunityPostComment):
            recipient = comment.parent.user if comment.parent_id else comment.post.user
            title = "Новый ответ в Сообществе" if comment.parent_id else "Новый комментарий к вашей записи"
            url = f"/community/#comment-{comment.pk}"
        else:
            recipient = comment.parent.user if comment.parent_id else comment.review.user
            title = "Новый ответ на комментарий" if comment.parent_id else "Новый комментарий к вашему отзыву"
            url = f"/reviews/#review-{comment.review_id}"
        if not recipient or recipient.pk == comment.user_id:
            return
        actor_name = comment.user.get_full_name() or comment.user.email
        create_notification(
            user=recipient,
            actor=comment.user,
            title=title,
            body=f"{actor_name}: {comment.text}",
            url=url,
            kind=UserNotification.KIND_REPLY,
        )

    def save_model(self, request, obj, form, change):
        was_approved = False
        if change and obj.pk:
            was_approved = type(obj).objects.filter(pk=obj.pk).values_list(
                "is_approved", flat=True
            ).first()
        super().save_model(request, obj, form, change)
        if not was_approved and obj.is_approved:
            self._notify_approved(obj)

    @admin.action(description="Одобрить выбранные комментарии")
    def approve_selected(self, request, queryset):
        if queryset.model is CommunityPostComment:
            pending = list(
                queryset.filter(is_approved=False).select_related(
                    "user", "parent__user", "post__user"
                )
            )
        else:
            pending = list(
                queryset.filter(is_approved=False).select_related(
                    "user", "parent__user", "review__user"
                )
            )
        updated = queryset.filter(is_approved=False).update(is_approved=True)
        for comment in pending:
            comment.is_approved = True
            self._notify_approved(comment)
        self.message_user(request, f"Одобрено комментариев: {updated}")

    @admin.action(description="Снять выбранные комментарии с публикации")
    def hide_selected(self, request, queryset):
        updated = queryset.update(is_approved=False)
        self.message_user(request, f"Снято с публикации комментариев: {updated}")


@admin.register(CommunityPostComment)
class CommunityPostCommentAdmin(CommentModerationAdminMixin, ModelAdmin):
    list_display = ("post", "user", "parent_author", "text_preview", "is_approved", "created_at")
    list_filter = (ApprovedStatusFilter, "created_at")
    list_editable = ("is_approved",)
    search_fields = ("post__title", "user__email", "user__username", "text")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("post", "user")

    @admin.display(description="Ответ на")
    def parent_author(self, obj):
        return obj.parent.user if obj.parent_id else "—"

    @admin.display(description="Комментарий")
    def text_preview(self, obj):
        return obj.text[:100]


@admin.register(ReviewComment)
class ReviewCommentAdmin(CommentModerationAdminMixin, ModelAdmin):
    list_display = ("review", "user", "parent_author", "text_preview", "is_approved", "created_at")
    list_filter = (ApprovedStatusFilter, "created_at")
    list_editable = ("is_approved",)
    search_fields = (
        "review__product__name", "review__author_name",
        "user__email", "user__username", "text",
    )
    readonly_fields = ("created_at",)
    autocomplete_fields = ("review", "user")

    @admin.display(description="Ответ на")
    def parent_author(self, obj):
        return obj.parent.user if obj.parent_id else "—"

    @admin.display(description="Комментарий")
    def text_preview(self, obj):
        return obj.text[:100]
