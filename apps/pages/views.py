from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render, get_object_or_404
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, HttpResponse, JsonResponse
from django.urls import reverse
from django.views.decorators.http import require_POST
from apps.catalog.models import Product, Category, Review
from .forms import CommunityPostForm
from .models import (
    CommunityPost, CommunityPostLike, CommunityPostDislike,
    CommunityPostBookmark, CommunityPostRepost, CommunityPostComment, ReviewComment,
)
from django.db.models import Count, Exists, OuterRef, Prefetch, Q


def _static_page(request, template, extra=None):
    ctx = extra or {}
    return render(request, f"pages/{template}.html", ctx)


def legal_document(request, slug):
    """Render admin-managed legal document (public offer, privacy, etc.).

    Falls back to 404 if the slug is not registered in LegalDocument.
    """
    from django.shortcuts import get_object_or_404
    from .models import LegalDocument

    doc = get_object_or_404(LegalDocument, slug=slug, is_active=True)
    context = {
        "doc": doc,
        "page_title": doc.title,
        "meta_description": doc.meta_description,
    }
    return render(request, "pages/legal_document.html", context)


def about(request):
    return _static_page(request, "about")


def faq(request):
    return _static_page(request, "faq")


def how_to_choose_coffee(request):
    return _static_page(request, "how_to_choose_coffee")


def grind_converter(request):
    return _static_page(request, "grind_converter")


def shipment_and_payment(request):
    return _static_page(request, "shipment_and_payment")


def discount_system(request):
    return _static_page(request, "discount_system")


def return_money(request):
    return _static_page(request, "return_money")


def coffee_in_office(request):
    return _static_page(request, "coffee_in_office")


def disabled(request):
    products = Product.objects.filter(is_active=False).select_related("category")[:50]
    return render(request, "pages/disabled.html", {"products": products})


def contact_us(request):
    return _static_page(request, "contact_us")


def partners(request):
    return _static_page(request, "partners")


def privacy(request):
    return _static_page(request, "privacy")


def user_agreement(request):
    return _static_page(request, "user_agreement")


def public_offer(request):
    return _static_page(request, "public_offer")


def sitemap_page(request):
    categories = Category.objects.filter(is_active=True, parent__isnull=True).order_by("order")
    pages_list = [
        ("Главная", "/"),
        ("Каталог", "/catalog/"),
        ("Чай", "/tea/"),
        ("Шоколад и сиропы", "/chocolate/"),
        ("Аксессуары", "/accessories/"),
        ("Подарочные наборы", "/giftbox/"),
        ("Подписка на кофе", "/subscription/"),
        ("Отзывы", "/reviews/"),
        ("Блог", "/blog/"),
        ("Сообщество", "/community/"),
        ("FAQ", "/faq/"),
        ("Как выбрать кофе", "/how-to-choose-coffee/"),
        ("Калькулятор помола", "/grind-converter/"),
        ("Доставка и оплата", "/shipment-and-payment/"),
        ("Система скидок", "/discount-system/"),
        ("Возврат денег", "/return-money/"),
        ("Кофе в офис", "/coffee-in-office/"),
        ("Контакты", "/contact-us/"),
        ("Партнёрам", "/partners/"),
        ("Политика конфиденциальности", "/privacy/"),
        ("Пользовательское соглашение", "/user-agreement/"),
        ("Публичная оферта", "/public-offer/"),
    ]
    return render(request, "pages/sitemap.html", {"categories": categories, "pages_list": pages_list})


def robots_txt(request):
    lines = [
        "User-agent: *",
        "Disallow: /admin/",
        "Disallow: /account/",
        "Disallow: /api/",
        "Disallow: /warehouse/",
        "",
        f"Sitemap: {request.scheme}://{request.get_host()}/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


def sitemap_xml(request):
    from django.contrib.sitemaps import Sitemap
    from django.contrib.sites.shortcuts import get_current_site

    pages = [
        (1.0, "weekly", request.build_absolute_uri("/")),
        (0.9, "daily", request.build_absolute_uri("/catalog/")),
        (0.8, "weekly", request.build_absolute_uri("/tea/")),
        (0.8, "weekly", request.build_absolute_uri("/chocolate/")),
        (0.8, "weekly", request.build_absolute_uri("/accessories/")),
        (0.8, "weekly", request.build_absolute_uri("/giftbox/")),
        (0.7, "monthly", request.build_absolute_uri("/subscription/")),
        (0.7, "weekly", request.build_absolute_uri("/blog/")),
        (0.6, "monthly", request.build_absolute_uri("/faq/")),
        (0.6, "monthly", request.build_absolute_uri("/how-to-choose-coffee/")),
        (0.6, "monthly", request.build_absolute_uri("/grind-converter/")),
        (0.6, "monthly", request.build_absolute_uri("/reviews/")),
        (0.6, "monthly", request.build_absolute_uri("/community/")),
        (0.5, "monthly", request.build_absolute_uri("/shipment-and-payment/")),
        (0.5, "monthly", request.build_absolute_uri("/discount-system/")),
        (0.5, "monthly", request.build_absolute_uri("/return-money/")),
        (0.5, "monthly", request.build_absolute_uri("/coffee-in-office/")),
        (0.5, "monthly", request.build_absolute_uri("/contact-us/")),
        (0.5, "monthly", request.build_absolute_uri("/partners/")),
        (0.4, "monthly", request.build_absolute_uri("/privacy/")),
        (0.4, "monthly", request.build_absolute_uri("/user-agreement/")),
        (0.4, "monthly", request.build_absolute_uri("/public-offer/")),
    ]

    products = Product.objects.filter(is_active=True)
    blog_posts = []
    try:
        from apps.blog.models import BlogPost
        blog_posts = BlogPost.objects.filter(is_published=True)
    except Exception:
        pass

    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'

    for priority, changefreq, loc in pages:
        xml += f"  <url>\n    <loc>{loc}</loc>\n    <changefreq>{changefreq}</changefreq>\n    <priority>{priority}</priority>\n  </url>\n"

    for product in products:
        xml += f"  <url>\n    <loc>{request.build_absolute_uri(product.get_absolute_url())}</loc>\n    <changefreq>weekly</changefreq>\n    <priority>0.7</priority>\n  </url>\n"

    for post in blog_posts:
        xml += f"  <url>\n    <loc>{request.build_absolute_uri(post.get_absolute_url())}</loc>\n    <changefreq>weekly</changefreq>\n    <priority>0.6</priority>\n  </url>\n"

    xml += "</urlset>"
    return HttpResponse(xml, content_type="application/xml")


def subscription(request):
    return _static_page(request, "subscription")


def reviews_page(request):
    from django.db.models import Avg, Count, Q
    qs = Review.objects.filter(is_approved=True).select_related("user", "product").prefetch_related(
        Prefetch(
            "public_comments",
            queryset=ReviewComment.objects.filter(is_approved=True)
            .select_related("user")
            .prefetch_related("user__addresses"),
        ),
        "user__addresses",
    )

    agg = qs.aggregate(
        shop_avg=Avg("rating"),
        delivery_avg=Avg("delivery_rating"),
        total=Count("id"),
    )
    shop_avg = round(agg["shop_avg"] or 0, 1)
    delivery_avg = round(agg["delivery_avg"] or 0, 1)
    total_count = agg["total"]

    shop_stars = [(s, qs.filter(rating=s).count()) for s in range(1, 6)]

    delivery_qs = qs.exclude(delivery_rating__isnull=True)
    delivery_stars = [(s, delivery_qs.filter(delivery_rating=s).count()) for s in range(1, 6)]

    operators = list(
        qs.exclude(delivery_operator="")
        .values_list("delivery_operator", flat=True)
        .distinct()
        .order_by("delivery_operator")
    )

    reviews = _prepare_review_threads(qs.order_by("-created_at")[:30])

    return render(request, "pages/reviews.html", {
        "reviews": reviews,
        "shop_avg": shop_avg,
        "delivery_avg": delivery_avg,
        "total_count": total_count,
        "shop_stars": shop_stars,
        "delivery_stars": delivery_stars,
        "operators": operators,
    })


def reviews_ajax(request):
    from django.db.models import Q
    qs = Review.objects.filter(is_approved=True).select_related("user", "product").prefetch_related(
        Prefetch(
            "public_comments",
            queryset=ReviewComment.objects.filter(is_approved=True)
            .select_related("user")
            .prefetch_related("user__addresses"),
        ),
        "user__addresses",
    )

    ratings = request.GET.getlist("rating")
    delivery_ratings = request.GET.getlist("delivery_rating")
    operators = request.GET.getlist("operator")
    q = request.GET.get("q", "").strip()

    if ratings:
        qs = qs.filter(rating__in=[int(r) for r in ratings if r.isdigit()])
    if delivery_ratings:
        qs = qs.filter(delivery_rating__in=[int(r) for r in delivery_ratings if r.isdigit()])
    if operators:
        qs = qs.filter(delivery_operator__in=operators)
    if q:
        qs = qs.filter(Q(text__icontains=q) | Q(delivery_text__icontains=q))

    reviews = _prepare_review_threads(qs.order_by("-created_at")[:60])
    return render(request, "pages/reviews_list_partial.html", {"reviews": reviews, "query": q})


def _prepare_review_threads(reviews):
    prepared = list(reviews)
    for review in prepared:
        comments = list(review.public_comments.all())
        by_parent = {}
        for comment in comments:
            comment.author_level = comment.user.get_level()
            comment.author_city = comment.user.get_city()
            by_parent.setdefault(comment.parent_id, []).append(comment)
        for comment in comments:
            comment.thread_replies = by_parent.get(comment.id, [])
        review.top_comments = by_parent.get(None, [])
    return prepared


def community(request, active_tab="best"):
    """Interactive community feed backed by CommunityPost and CommunityPostLike."""
    form = CommunityPostForm()
    if request.method == "POST":
        if not request.user.is_authenticated:
            messages.error(request, "Войдите в аккаунт, чтобы добавить запись.")
            return redirect("/login/?next=/community/")
        form = CommunityPostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.user = request.user
            post.save()
            messages.success(request, "Запись опубликована в сообществе.")
            if request.headers.get("X-Requested-With") != "XMLHttpRequest":
                return redirect("pages:community")

    q = request.GET.get("q", "").strip()
    selected_scope = request.GET.get("scope", "all")
    scope_labels = {
        "all": "Везде",
        "authors": "По авторам",
        "products": "По сортам",
    }
    if selected_scope not in scope_labels:
        selected_scope = "all"
    user_id = request.user.id if request.user.is_authenticated else None
    my_like = CommunityPostLike.objects.filter(post_id=OuterRef("pk"), user_id=user_id)
    my_dislike = CommunityPostDislike.objects.filter(post_id=OuterRef("pk"), user_id=user_id)
    my_bookmark = CommunityPostBookmark.objects.filter(post_id=OuterRef("pk"), user_id=user_id)
    my_repost = CommunityPostRepost.objects.filter(post_id=OuterRef("pk"), user_id=user_id)
    posts_qs = CommunityPost.objects.filter(is_published=True).select_related("user").prefetch_related(
        Prefetch(
            "comments",
            queryset=CommunityPostComment.objects.filter(is_approved=True)
            .select_related("user")
            .prefetch_related("user__addresses"),
        ),
        "user__addresses",
    )
    if q:
        content_query = Q(title__icontains=q) | Q(text__icontains=q)
        author_query = (
            Q(user__first_name__icontains=q)
            | Q(user__last_name__icontains=q)
            | Q(user__email__icontains=q)
        )
        if selected_scope == "authors":
            posts_qs = posts_qs.filter(author_query)
        elif selected_scope == "products":
            posts_qs = posts_qs.filter(content_query)
        else:
            posts_qs = posts_qs.filter(content_query | author_query)
    if active_tab == "bookmarks":
        posts_qs = posts_qs.filter(bookmarks__user_id=user_id) if user_id else posts_qs.none()
    posts_qs = posts_qs.annotate(
        like_count=Count("likes", distinct=True),
        dislike_count=Count("dislikes", distinct=True),
        comment_count=Count("comments", filter=Q(comments__is_approved=True), distinct=True),
        repost_count=Count("reposts", distinct=True),
        liked_by_me=Exists(my_like), disliked_by_me=Exists(my_dislike),
        bookmarked_by_me=Exists(my_bookmark), reposted_by_me=Exists(my_repost),
    )
    posts_qs = posts_qs.order_by("-created_at") if active_tab in ("new", "bookmarks") else posts_qs.order_by("-like_count", "-created_at")
    posts = list(posts_qs[:24])
    for post in posts:
        post.author_level = post.user.get_level()
        post.author_city = post.user.get_city()
        comments = list(post.comments.all())
        by_parent = {}
        for comment in comments:
            comment.author_level = comment.user.get_level()
            comment.author_city = comment.user.get_city()
            by_parent.setdefault(comment.parent_id, []).append(comment)
        for comment in comments:
            comment.thread_replies = by_parent.get(comment.id, [])
        post.top_comments = by_parent.get(None, [])
    context = {
            "form": form,
            "community_posts": posts,
            "active_tab": active_tab,
            "query": q,
            "selected_scope": selected_scope,
            "selected_scope_label": scope_labels[selected_scope],
            "show_channels": active_tab == "channels",
            "current_user_level": request.user.get_level() if request.user.is_authenticated else None,
            "community_channels": [
                {"title": "Заваривание", "description": "Рецепты, вода и настройки кофейных устройств"},
                {"title": "Новинки Aspect Coffee", "description": "Обсуждаем свежую обжарку и сезонные сорта"},
                {"title": "Встречи и дегустации", "description": "Анонсы событий и встречи любителей кофе"},
            ],
    }
    return render(request, "pages/community_live.html", context)


def community_new(request):
    return community(request, active_tab="new")


def community_channels(request):
    return community(request, active_tab="channels")


def community_bookmarks(request):
    return community(request, active_tab="bookmarks")


def community_rules(request):
    return _static_page(request, "community_rules")


@login_required
@require_POST
def community_post_delete(request, pk):
    """Delete a community post owned by the current user."""
    post = get_object_or_404(CommunityPost, pk=pk, user=request.user)
    post.delete()
    if request.headers.get("HX-Request"):
        return HttpResponse("")
    messages.success(request, "Запись удалена")
    return redirect(request.META.get("HTTP_REFERER", "users:community_profile"))


@login_required
def community_post_edit(request, pk):
    """Edit a community post owned by the current user."""
    post = get_object_or_404(CommunityPost, pk=pk, user=request.user)
    if request.method == "POST":
        form = CommunityPostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
            messages.success(request, "Запись обновлена")
            return redirect("users:community_profile")
    else:
        form = CommunityPostForm(instance=post)
    return render(request, "pages/community_edit.html", {"form": form, "post": post})


@require_POST
def community_post_like_toggle(request, pk):
    """Toggle a like on a community post. Self-likes are rejected."""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "login_required", "redirect": "/login/?next=/community/"}, status=401)
    post = get_object_or_404(CommunityPost, pk=pk, is_published=True)
    if post.user_id == request.user.id:
        return JsonResponse({"error": "self_like_forbidden"}, status=403)
    add = request.POST.get("add", "true").lower() in ("true", "1", "yes")
    if add:
        CommunityPostLike.objects.get_or_create(post=post, user=request.user)
        CommunityPostDislike.objects.filter(post=post, user=request.user).delete()
    else:
        CommunityPostLike.objects.filter(post=post, user=request.user).delete()
    like_count = post.likes.count()
    return JsonResponse({"ok": True, "post_id": post.pk, "liked": add, "like_count": like_count, "dislike_count": post.dislikes.count()})


def _community_action_login_required(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "login_required", "redirect": "/login/?next=/community/"}, status=401)


@require_POST
def community_post_dislike_toggle(request, pk):
    denied = _community_action_login_required(request)
    if denied:
        return denied
    post = get_object_or_404(CommunityPost, pk=pk, is_published=True)
    if post.user_id == request.user.id:
        return JsonResponse({"error": "self_vote_forbidden"}, status=403)
    add = request.POST.get("add", "true").lower() in ("true", "1", "yes")
    if add:
        CommunityPostDislike.objects.get_or_create(post=post, user=request.user)
        CommunityPostLike.objects.filter(post=post, user=request.user).delete()
    else:
        CommunityPostDislike.objects.filter(post=post, user=request.user).delete()
    return JsonResponse({"ok": True, "active": add, "count": post.dislikes.count(), "like_count": post.likes.count()})


@require_POST
def community_post_bookmark_toggle(request, pk):
    denied = _community_action_login_required(request)
    if denied:
        return denied
    post = get_object_or_404(CommunityPost, pk=pk, is_published=True)
    bookmark, created = CommunityPostBookmark.objects.get_or_create(post=post, user=request.user)
    if not created:
        bookmark.delete()
    return JsonResponse({"ok": True, "active": created})


@require_POST
def community_post_repost_toggle(request, pk):
    denied = _community_action_login_required(request)
    if denied:
        return denied
    post = get_object_or_404(CommunityPost, pk=pk, is_published=True)
    if post.user_id == request.user.id:
        return JsonResponse({"error": "self_repost_forbidden"}, status=403)
    repost, created = CommunityPostRepost.objects.get_or_create(post=post, user=request.user)
    if not created:
        repost.delete()
    return JsonResponse({"ok": True, "active": created, "count": post.reposts.count()})


@require_POST
def community_post_comment_create(request, pk):
    denied = _community_action_login_required(request)
    if denied:
        return denied
    post = get_object_or_404(CommunityPost, pk=pk, is_published=True)
    text = request.POST.get("text", "").strip()
    if not text:
        return JsonResponse({"error": "empty_comment"}, status=400)
    parent = None
    parent_id = request.POST.get("parent_id")
    if parent_id:
        parent = get_object_or_404(
            CommunityPostComment,
            pk=parent_id,
            post=post,
            is_approved=True,
        )
    comment = CommunityPostComment.objects.create(
        post=post,
        user=request.user,
        parent=parent,
        text=text[:1000],
        is_approved=False,
    )

    recipient = post.user if parent is None else parent.user
    if parent is not None:
        requested_user_id = request.POST.get("reply_to_user_id")
        if requested_user_id and requested_user_id.isdigit():
            requested_user_id = int(requested_user_id)
            allowed = requested_user_id == parent.user_id or parent.replies.filter(user_id=requested_user_id).exists()
            if allowed:
                from apps.users.models import User
                recipient = User.objects.filter(pk=requested_user_id, is_active=True).first() or recipient
    if comment.is_approved and recipient and recipient.pk != request.user.pk:
        from apps.users.models import UserNotification
        from apps.users.notifications import create_notification
        actor_name = request.user.get_full_name() or request.user.email
        create_notification(
            user=recipient,
            actor=request.user,
            title="Новый ответ в Сообществе" if parent else "Новый комментарий к вашей записи",
            body=f"{actor_name}: {comment.text}",
            url=f"/community/#comment-{comment.pk}",
            kind=UserNotification.KIND_REPLY,
        )
    return JsonResponse({
        "ok": True,
        "pending_moderation": True,
        "count": post.comments.filter(is_approved=True).count(),
        "message": "Комментарий отправлен на модерацию и появится после одобрения.",
    })


@require_POST
def review_comment_create(request, pk):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "login_required", "redirect": "/login/?next=/reviews/"}, status=401)
    review = get_object_or_404(Review, pk=pk, is_approved=True)
    text = request.POST.get("text", "").strip()
    if not text:
        return JsonResponse({"error": "empty_comment"}, status=400)
    parent = None
    parent_id = request.POST.get("parent_id")
    if parent_id:
        parent = get_object_or_404(
            ReviewComment,
            pk=parent_id,
            review=review,
            is_approved=True,
        )
    comment = ReviewComment.objects.create(
        review=review,
        user=request.user,
        parent=parent,
        text=text[:1000],
        is_approved=False,
    )

    recipient = review.user if parent is None else parent.user
    if parent is not None:
        requested_user_id = request.POST.get("reply_to_user_id")
        if requested_user_id and requested_user_id.isdigit():
            requested_user_id = int(requested_user_id)
            allowed = requested_user_id == parent.user_id or parent.replies.filter(user_id=requested_user_id).exists()
            if allowed:
                from apps.users.models import User
                recipient = User.objects.filter(pk=requested_user_id, is_active=True).first() or recipient
    if comment.is_approved and recipient and recipient.pk != request.user.pk:
        from apps.users.models import UserNotification
        from apps.users.notifications import create_notification
        actor_name = request.user.get_full_name() or request.user.email
        create_notification(
            user=recipient,
            actor=request.user,
            title="Новый ответ на комментарий" if parent else "Новый комментарий к вашему отзыву",
            body=f"{actor_name}: {comment.text}",
            url=f"/reviews/#review-{review.pk}",
            kind=UserNotification.KIND_REPLY,
        )
    return JsonResponse({
        "ok": True,
        "pending_moderation": True,
        "message": "Комментарий отправлен на модерацию и появится после одобрения.",
    })


@login_required
@require_POST
def reviews_create(request):
    import json
    from apps.catalog.models import Review, Product

    rating = int(request.POST.get("rating", 0))
    delivery_rating = request.POST.get("delivery_rating")
    text = request.POST.get("text", "")
    delivery_text = request.POST.get("delivery_text", "")
    delivery_operator = request.POST.get("delivery_operator", "")

    errors = {}
    if rating < 1 or rating > 5:
        errors["rating"] = "Рейтинг магазина от 1 до 5"
    if not text.strip():
        errors["text"] = "Напишите отзыв"

    if delivery_rating:
        delivery_rating = int(delivery_rating)
        if delivery_rating < 1 or delivery_rating > 5:
            errors["delivery_rating"] = "Рейтинг доставки от 1 до 5"
    else:
        delivery_rating = None

    if errors:
        return JsonResponse({"success": False, "errors": errors})

    default_product = Product.objects.order_by("id").first()
    if not default_product:
        return JsonResponse({"success": False, "errors": {"general": "Нет товаров"}})

    review = Review.objects.create(
        product=default_product,
        user=request.user,
        rating=rating,
        delivery_rating=delivery_rating,
        text=text.strip(),
        delivery_text=delivery_text.strip(),
        delivery_operator=delivery_operator.strip(),
        status=Review.STATUS_NEW,
    )

    return JsonResponse({"success": True, "review_id": review.pk})
