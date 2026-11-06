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
        "is_published", "is_featured", "created_at",
    )
    list_filter = ("is_published", "is_featured", "category")
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
            "fields": ("is_published", "is_featured", "created_at", "updated_at"),
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


@admin.register(ArticleComment)
class ArticleCommentAdmin(ModelAdmin):
    list_display = ("post", "user", "text_preview", "is_approved", "created_at")
    list_filter = ("is_approved", "created_at")
    search_fields = ("post__title", "user__email", "text")
    autocomplete_fields = ("post", "user")

    @admin.display(description="Комментарий")
    def text_preview(self, obj):
        return obj.text[:100]
