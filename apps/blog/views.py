from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.html import strip_tags
from .models import (
    BlogPost, BlogCategory, BlogSeries, BlogSeriesVisit,
    ArticleBookmark, ArticleReadHistory, ArticleLike, ArticleComment, BlogPostView,
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


def _liked_bookmarked_ids(request):
    liked_ids, bookmarked_ids = set(), set()
    if request.user.is_authenticated:
        liked_ids = set(ArticleLike.objects.filter(user=request.user).values_list("post_id", flat=True))
        bookmarked_ids = set(ArticleBookmark.objects.filter(user=request.user).values_list("post_id", flat=True))
    return liked_ids, bookmarked_ids


def _decorate_posts(page_items, liked_ids, bookmarked_ids):
    """Attach card presentation data: reading time, short views and
    the repeating feed pattern [wide + narrow] -> [3 columns]."""
    for idx, post in enumerate(page_items):
        post.reading_minutes = _reading_minutes(post)
        post.views_display = _short_count(post.unique_views_count)
        post.is_wide = idx % 5 == 0
        post.is_liked = post.id in liked_ids
        post.is_bookmarked = post.id in bookmarked_ids


def _journal_series(request):
    if request.user.is_authenticated:
        visited = set(BlogSeriesVisit.objects.filter(user=request.user).values_list("series_id", flat=True))
    else:
        visited = set(request.session.get("visited_blog_series", []))
    series_list = list(
        BlogSeries.objects.filter(is_active=True).exclude(id__in=visited)
        .prefetch_related("series_items__post").order_by("order", "id")
    )
    result = []
    for series in series_list:
        items = [item for item in series.series_items.all() if item.post.is_published]
        if not items:
            continue
        series.lead_post = items[0].post
        series.article_count = len(items)
        series.count_label = f"{len(items)} {_ru_plural(len(items), 'статья', 'статьи', 'статей')}"
        series.card_url = f"{series.lead_post.get_absolute_url()}?series={series.slug}"
        result.append(series)
    return result


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
    journal_series = _journal_series(request)

    liked_ids, bookmarked_ids = _liked_bookmarked_ids(request)
    _decorate_posts(page_obj.object_list, liked_ids, bookmarked_ids)

    context = {
        "posts": page_obj,
        "page_obj": page_obj,
        "categories": categories,
        "current_category": current_category,
        "search_query": search_query,
        "selected_sort": selected_sort,
        "journal_series": journal_series,
        "bookmarked_ids": bookmarked_ids,
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

    active_series = None
    series_posts = []
    series_slug = request.GET.get("series", "").strip()
    if series_slug:
        active_series = get_object_or_404(BlogSeries, slug=series_slug, is_active=True)
        if request.user.is_authenticated:
            BlogSeriesVisit.objects.update_or_create(user=request.user, series=active_series)
        else:
            visited = set(request.session.get("visited_blog_series", []))
            visited.add(active_series.id)
            request.session["visited_blog_series"] = list(visited)
        series_posts = [
            item.post for item in active_series.series_items.select_related("post").all()
            if item.post.is_published and item.post_id != post.id
        ]
    recent_posts = BlogPost.objects.filter(is_published=True).exclude(id=post.id)[:5]
    categories = BlogCategory.objects.all()

    post.reading_minutes = _reading_minutes(post)
    post.views_display = _short_count(post.unique_views_count)
    post.show_updated_date = post.updated_at.date() != post.created_at.date()

    # Track reading history for logged-in users
    is_bookmarked = False
    is_liked = False
    if request.user.is_authenticated:
        ArticleReadHistory.objects.update_or_create(
            user=request.user, post=post,
            defaults={}  # auto_now=True on read_at will update it
        )
        is_bookmarked = ArticleBookmark.objects.filter(user=request.user, post=post).exists()
        is_liked = ArticleLike.objects.filter(user=request.user, post=post).exists()

    context = {
        "post": post,
        "recent_posts": recent_posts,
        "categories": categories,
        "is_bookmarked": is_bookmarked,
        "is_liked": is_liked,
        "article_comments": post.comments.filter(is_approved=True),
        "active_series": active_series,
        "series_posts": series_posts,
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
    journal_series = _journal_series(request)

    liked_ids, bookmarked_ids = _liked_bookmarked_ids(request)
    _decorate_posts(page_obj.object_list, liked_ids, bookmarked_ids)

    context = {
        "posts": page_obj,
        "page_obj": page_obj,
        "categories": categories,
        "current_category": slug,
        "selected_sort": selected_sort,
        "journal_series": journal_series,
        "bookmarked_ids": bookmarked_ids,
        "posts_count_label": f"{paginator.count} {_ru_plural(paginator.count, 'статья', 'статьи', 'статей')}",
    }
    return render(request, "blog/index.html", context)


@require_POST
def toggle_bookmark(request, slug):
    """Toggle article bookmark for authenticated users. Returns JSON."""
    if not request.user.is_authenticated:
        return JsonResponse({"ok": False, "error": "login_required"}, status=401)
    post = get_object_or_404(BlogPost, slug=slug, is_published=True)
    bookmark, created = ArticleBookmark.objects.get_or_create(user=request.user, post=post)
    if not created:
        bookmark.delete()
        bookmarked = False
    else:
        bookmarked = True
    total = ArticleBookmark.objects.filter(user=request.user).count()
    return JsonResponse({"ok": True, "bookmarked": bookmarked, "total": total})


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
