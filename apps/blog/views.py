from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.html import strip_tags
from .models import (
    BlogPost, BlogCategory,
    ArticleLike, ArticleComment, BlogPostView,
)


def _posts_with_stats():
    return BlogPost.objects.filter(is_published=True).select_related("category").annotate(
        likes_count=Count("likes", distinct=True),
        comments_count=Count("comments", filter=Q(comments__is_approved=True), distinct=True),
        unique_views_count=Count("view_records", distinct=True),
    )


def _short_count(value):
    """Format a counter the way the reference does: 999 -> 999, 2300 -> 2K."""
    value = value or 0
    if value >= 1000:
        short = value / 1000.0
        text = f"{short:.1f}".rstrip("0").rstrip(".")
        return f"{text}K"
    return str(value)


def _ru_plural(number, one, few, many):
    n = abs(number) % 100
    if 11 <= n <= 14:
        return many
    n %= 10
    if n == 1:
        return one
    if 2 <= n <= 4:
        return few
    return many


def _reading_minutes(post):
    words = len(strip_tags(post.content or "").split())
    return max(1, round(words / 170))


def _liked_ids(request):
    if request.user.is_authenticated:
        return set(ArticleLike.objects.filter(user=request.user).values_list("post_id", flat=True))
    return set()


def _decorate_posts(page_items, liked_ids):
    """Attach reading time and view count used by the journal cards."""
    for post in page_items:
        post.reading_minutes = _reading_minutes(post)
        post.views_display = _short_count(post.unique_views_count)
        post.is_liked = post.id in liked_ids


def index(request):
    current_category = request.GET.get("category", "").strip()
    search_query = request.GET.get("q", "").strip()
    selected_sort = request.GET.get("sort", "new")
    posts_list = _posts_with_stats()
    if current_category:
        posts_list = posts_list.filter(category__slug=current_category)
    if search_query:
        posts_list = posts_list.filter(
            Q(title__icontains=search_query)
            | Q(short_description__icontains=search_query)
            | Q(content__icontains=search_query)
        )
    if selected_sort == "old":
        posts_list = posts_list.order_by("created_at")
    else:
        selected_sort = "new"
        posts_list = posts_list.order_by("-created_at")
    paginator = Paginator(posts_list, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    categories = BlogCategory.objects.all()

    liked_ids = _liked_ids(request)
    _decorate_posts(page_obj.object_list, liked_ids)

    context = {
        "posts": page_obj,
        "page_obj": page_obj,
        "categories": categories,
        "current_category": current_category,
        "search_query": search_query,
        "selected_sort": selected_sort,
        "liked_ids": liked_ids,
        "posts_count_label": f"{paginator.count} {_ru_plural(paginator.count, 'статья', 'статьи', 'статей')}",
    }
    return render(request, "blog/index.html", context)


def _track_unique_view(request, post):
    """Persist one view per authenticated user or anonymous browser session."""
    session_key = request.session.session_key
    if not session_key:
        request.session.create()
        session_key = request.session.session_key

    if request.user.is_authenticated:
        visitor_key = f"user:{request.user.pk}"
        view, _ = BlogPostView.objects.get_or_create(
            post=post,
            visitor_key=visitor_key,
            defaults={"user": request.user, "session_key": session_key or ""},
        )
        BlogPostView.objects.filter(pk=view.pk).update(
            user=request.user,
            session_key=session_key or "",
            last_viewed_at=timezone.now(),
        )
        # If this browser viewed the article before login, merge that guest
        # record into the authenticated viewer instead of counting twice.
        if session_key:
            BlogPostView.objects.filter(
                post=post,
                visitor_key=f"session:{session_key}",
            ).exclude(pk=view.pk).delete()
    else:
        visitor_key = f"session:{session_key}"
        view, created = BlogPostView.objects.get_or_create(
            post=post,
            visitor_key=visitor_key,
            defaults={"session_key": session_key},
        )
        if not created:
            BlogPostView.objects.filter(pk=view.pk).update(last_viewed_at=timezone.now())

    real_count = BlogPostView.objects.filter(post=post).count()
    BlogPost.objects.filter(pk=post.pk).update(views_count=real_count)
    post.views_count = real_count
    post.unique_views_count = real_count


def detail(request, slug):
    post = get_object_or_404(_posts_with_stats().prefetch_related("comments__user"), slug=slug)
    _track_unique_view(request, post)

    recent_posts = BlogPost.objects.filter(is_published=True).exclude(id=post.id)[:5]
    categories = BlogCategory.objects.all()

    post.reading_minutes = _reading_minutes(post)
    post.views_display = _short_count(post.unique_views_count)
    post.show_updated_date = post.updated_at.date() != post.created_at.date()

    # ArticleReadHistory was removed — no per-user read history is written here.
    is_liked = False
    if request.user.is_authenticated:
        is_liked = ArticleLike.objects.filter(user=request.user, post=post).exists()

    context = {
        "post": post,
        "recent_posts": recent_posts,
        "categories": categories,
        "is_liked": is_liked,
        "article_comments": post.comments.filter(is_approved=True),
    }
    return render(request, "blog/detail.html", context)


def category(request, slug):
    """Blog category page — filters posts by category slug."""
    cat = get_object_or_404(BlogCategory, slug=slug)
    selected_sort = request.GET.get("sort", "new")
    posts_list = _posts_with_stats().filter(category=cat)
    if selected_sort == "old":
        posts_list = posts_list.order_by("created_at")
    else:
        selected_sort = "new"
        posts_list = posts_list.order_by("-created_at")
    paginator = Paginator(posts_list, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    categories = BlogCategory.objects.all()

    liked_ids = _liked_ids(request)
    _decorate_posts(page_obj.object_list, liked_ids)

    context = {
        "posts": page_obj,
        "page_obj": page_obj,
        "categories": categories,
        "current_category": slug,
        "selected_sort": selected_sort,
        "liked_ids": liked_ids,
        "posts_count_label": f"{paginator.count} {_ru_plural(paginator.count, 'статья', 'статьи', 'статей')}",
    }
    return render(request, "blog/index.html", context)


@require_POST
def toggle_like(request, slug):
    if not request.user.is_authenticated:
        return JsonResponse({"ok": False, "error": "login_required"}, status=401)
    post = get_object_or_404(BlogPost, slug=slug, is_published=True)
    like, created = ArticleLike.objects.get_or_create(user=request.user, post=post)
    if not created:
        like.delete()
    return JsonResponse({"ok": True, "liked": created, "count": post.likes.count()})


@require_POST
def add_comment(request, slug):
    if not request.user.is_authenticated:
        return JsonResponse({"ok": False, "error": "login_required"}, status=401)
    post = get_object_or_404(BlogPost, slug=slug, is_published=True)
    text = request.POST.get("text", "").strip()
    if not text:
        return JsonResponse({"ok": False, "error": "empty_comment"}, status=400)
    comment = ArticleComment.objects.create(user=request.user, post=post, text=text[:2000])
    return JsonResponse({
        "ok": True,
        "count": post.comments.filter(is_approved=True).count(),
        "comment": {
            "author": request.user.first_name or "Пользователь",
            "text": comment.text,
            "date": comment.created_at.strftime("%d.%m.%Y %H:%M"),
        },
    })