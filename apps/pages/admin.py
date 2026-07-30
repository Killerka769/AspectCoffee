from django.contrib import admin
from django.db.models import Count, Q
from unfold.admin import ModelAdmin, TabularInline
from .models import (
    Banner, CommunityPost, CommunityPostBookmark, CommunityPostComment,
    CommunityPostDislike, CommunityPostLike, CommunityPostRepost,
    ReviewComment, LegalDocument, SiteLink,
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


@admin.register(Banner)
class BannerAdmin(ModelAdmin):
    list_display = ("title", "slot", "is_active", "order", "created_at")
    list_filter = ("slot", "is_active")
    list_editable = ("is_active", "order")
    search_fields = ("title", "description", "link_url")


@admin.register(SiteLink)
class SiteLinkAdmin(ModelAdmin):
    list_display = ("label", "group", "url", "is_active", "order")
    list_filter = ("group", "is_active", "open_new_tab")
    list_editable = ("is_active", "order")
    search_fields = ("label", "url")


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


@admin.register(CommunityPost)
class CommunityPostAdmin(ModelAdmin):
    list_display = ("title", "user", "likes_total", "comments_total", "is_published", "created_at")
    list_filter = ("is_published", "created_at")
    list_editable = ("is_published",)
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



@admin.register(CommunityPostLike)
class CommunityPostLikeAdmin(ModelAdmin):
    list_display = ("post", "user", "created_at")
    list_filter = ("created_at",)
    search_fields = ("post__title", "user__email", "user__username")
    readonly_fields = ("created_at",)


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
    list_filter = ("is_approved", "created_at")
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
    list_filter = ("is_approved", "created_at")
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


class ReadOnlyCommunityActivityAdmin(ModelAdmin):
    list_filter = ("created_at",)
    search_fields = ("post__title", "user__email")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(CommunityPostBookmark)
class CommunityPostBookmarkAdmin(ReadOnlyCommunityActivityAdmin):
    list_display = ("post", "user", "created_at")
    readonly_fields = ("post", "user", "created_at")


@admin.register(CommunityPostDislike)
class CommunityPostDislikeAdmin(ReadOnlyCommunityActivityAdmin):
    list_display = ("post", "user", "created_at")
    readonly_fields = ("post", "user", "created_at")


@admin.register(CommunityPostRepost)
class CommunityPostRepostAdmin(ReadOnlyCommunityActivityAdmin):
    list_display = ("post", "user", "created_at")
    readonly_fields = ("post", "user", "created_at")
