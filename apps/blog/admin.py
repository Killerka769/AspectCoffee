from django.contrib import admin
from django.db.models import Count, Q
from unfold.admin import ModelAdmin, TabularInline
from .models import (
    BlogCategory, BlogPost, BlogPostView,
    ArticleComment, ArticleLike,
)


@admin.register(BlogCategory)
class BlogCategoryAdmin(ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = ("name", "slug", "description")
    search_fields = ("name", "slug", "description")


class BlogPostViewInline(TabularInline):
    model = BlogPostView
    extra = 0
    fields = ("viewer", "first_viewed_at", "last_viewed_at")
    readonly_fields = fields
    can_delete = False

    @admin.display(description="Посетитель")
    def viewer(self, obj):
        return obj.user or f"Гость · {obj.session_key[:8]}"

    def has_add_permission(self, request, obj=None):
        return False


class ArticleLikeInline(TabularInline):
    model = ArticleLike
    extra = 0
    fields = ("user", "created_at")
    readonly_fields = fields
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class ArticleCommentInline(TabularInline):
    model = ArticleComment
    extra = 0
    fields = ("user", "text", "is_approved", "created_at")
    readonly_fields = ("created_at",)


@admin.register(BlogPost)
class BlogPostAdmin(ModelAdmin):
    prepopulated_fields = {"slug": ("title",)}
    list_display = (
        "title", "category", "unique_views", "likes_total", "comments_total",
        "is_published", "created_at",
    )
    list_filter = ("is_published", "category")
    search_fields = ("title", "short_description")
    readonly_fields = ("unique_views", "likes_total", "comments_total", "created_at", "updated_at")
    inlines = (BlogPostViewInline, ArticleLikeInline, ArticleCommentInline)
    fieldsets = (
        ("Основная информация", {
            "fields": ("category", "title", "slug", "image", "short_description"),
        }),
        ("Содержание статьи", {
            "fields": ("content",),
        }),
        ("Публикация", {
            "fields": ("is_published", "created_at", "updated_at"),
        }),
        ("Реальная статистика", {
            "fields": ("unique_views", "likes_total", "comments_total"),
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _unique_views=Count("view_records", distinct=True),
            _likes_total=Count("likes", distinct=True),
            _comments_total=Count("comments", filter=Q(comments__is_approved=True), distinct=True),
        )

    @admin.display(description="Просмотры", ordering="_unique_views")
    def unique_views(self, obj):
        return getattr(obj, "_unique_views", obj.view_records.count())

    @admin.display(description="Лайки", ordering="_likes_total")
    def likes_total(self, obj):
        return getattr(obj, "_likes_total", obj.likes.count())

    @admin.display(description="Комментарии", ordering="_comments_total")
    def comments_total(self, obj):
        return getattr(obj, "_comments_total", obj.comments.filter(is_approved=True).count())


class CommentPublicationFilter(admin.SimpleListFilter):
    title = "Статус"
    parameter_name = "publication"

    def lookups(self, request, model_admin):
        return (("yes", "Опубликовано"), ("no", "На модерации"))

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.filter(is_approved=True)
        if self.value() == "no":
            return queryset.filter(is_approved=False)
        return queryset


@admin.register(ArticleComment)
class ArticleCommentAdmin(ModelAdmin):
    list_display = ("post", "user", "text_preview", "is_approved", "created_at")
    list_filter = (CommentPublicationFilter, "created_at")
    list_editable = ("is_approved",)
    search_fields = ("post__title", "user__email", "text")
    autocomplete_fields = ("post", "user")
    actions = ("publish_selected", "hide_selected")

    @admin.action(description="Опубликовать выбранные комментарии")
    def publish_selected(self, request, queryset):
        updated = queryset.filter(is_approved=False).update(is_approved=True)
        self.message_user(request, f"Опубликовано комментариев: {updated}")

    @admin.action(description="Снять выбранные комментарии с публикации")
    def hide_selected(self, request, queryset):
        updated = queryset.filter(is_approved=True).update(is_approved=False)
        self.message_user(request, f"Снято с публикации комментариев: {updated}")

    @admin.display(description="Комментарий")
    def text_preview(self, obj):
        return obj.text[:100]
