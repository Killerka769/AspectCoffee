from django.core.paginator import Paginator
from django.db.models import Avg, Case, Count, DecimalField, F, IntegerField, Min, Q, Sum, When
from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST
from django.utils.html import strip_tags
from apps.orders.models import OrderItem
from .models import (
    BrewMethod, CatalogFilterSettings, Category, FlavorNote,
    Product, Review, PromoSlide, Cafe, SiteSettings,
)
from .situational import SITUATIONAL_TABS, apply_situational
from .facets import build_facets
import json
import math
import re
from html import unescape


class VariablePaginator(Paginator):
    def __init__(self, object_list, per_page, first_page_size, **kwargs):
        self.first_page_size = first_page_size
        super().__init__(object_list, per_page, **kwargs)

    @property
    def num_pages(self):
        if self.count == 0:
            return 1
        if self.count <= self.first_page_size:
            return 1
        return 1 + math.ceil((self.count - self.first_page_size) / self.per_page)

    def page(self, number):
        number = self.validate_number(number)
        if number == 1:
            bottom = 0
            top = min(self.first_page_size, self.count)
        else:
            bottom = self.first_page_size + (number - 2) * self.per_page
            top = min(bottom + self.per_page, self.count)
        return self._get_page(self.object_list[bottom:top], number, self)


QUICK_FILTER_OPTIONS = (
    {"id": "week_special", "label": "Sort nedeli"},
    {"id": "popular", "label": "Populyarniy"},
    {"id": "new", "label": "Noviy"},
    {"id": "recommended", "label": "Rekomenduem"},
)

ROAST_FILTER_OPTIONS = (
    {"id": "light", "label": "Light"},
    {"id": "medium", "label": "Medium"},
    {"id": "dark", "label": "Dark"},
    {"id": "dark_for_milk", "label": "Dark for milk"},
)

ACIDITY_OPTIONS = (
    {"id": "low", "label": "Low"},
    {"id": "medium", "label": "Medium"},
    {"id": "high", "label": "High"},
)

BODY_OPTIONS = (
    {"id": "low", "label": "Low"},
    {"id": "medium", "label": "Medium"},
    {"id": "high", "label": "High"},
)

FLAVOR_FILTER_OPTIONS = (
    {"id": "shokolad", "label": "Shokolad"},
    {"id": "orex", "label": "Orex"},
    {"id": "cveti", "label": "Cveti"},
    {"id": "citrus", "label": "Citrus"},
    {"id": "frukty", "label": "Frukty"},
    {"id": "yagody", "label": "Yagody"},
    {"id": "alkohol", "label": "Alkohol"},
    {"id": "fanki", "label": "Fanki"},
)

PROCESSING_FILTER_OPTIONS = (
    {"id": "mytoy", "label": "Mytoy"},
    {"id": "naturalnyy", "label": "Naturalnyy"},
    {"id": "hani", "label": "Hani"},
    {"id": "fanki", "label": "Fanki"},
    {"id": "smes", "label": "Smes"},
    {"id": "drugoy", "label": "Drugoy"},
)

COUNTRY_FILTER_OPTIONS = (
    {"id": "braziliya", "label": "Braziliya"},
    {"id": "efiopiya", "label": "Efiopiya"},
    {"id": "kolumbiya", "label": "Kolumbiya"},
    {"id": "keniya", "label": "Keniya"},
    {"id": "ruanda", "label": "Ruanda"},
    {"id": "gvatemala", "label": "Gvatemala"},
    {"id": "kosta-rika", "label": "Kosta-Rika"},
)

FEATURE_FILTER_OPTIONS = (
    {"id": "blend", "label": "Smes"},
    {"id": "decaf", "label": "Bez kofeina"},
    {"id": "single_origin", "label": "Monosort"},
    {"id": "micro_lot", "label": "Mikrolot"},
    {"id": "for_milk", "label": "Dlya moloka"},
)

FLAVOR_KEYWORDS = {
    "shokolad": ("шоколад", "какао", "cocoa", "chocolate", "брауни"),
    "orex": ("орех", "nut", "миндаль", "фундук", "natty"),
    "cveti": ("цвет", "floral", "жасмин", "флорал"),
    "citrus": ("цитрус", "citrus", "лимон", "апельсин", "orange", "grapefruit"),
    "frukty": ("фрукт", "fruit", "персик", "манго", "яблок", "фрутти"),
    "yagody": ("ягод", "berry", "вишн", "смородин", "малина", "бэрри"),
    "alkohol": ("алког", "ром", "вино", "ликер", "whisky", "бурбон"),
    "fanki": ("фанк", "funk", "фермент", "анаэроб", "anaerob"),
}

PROCESSING_KEYWORDS = {
    "mytoy": ("мытый", "washed"),
    "naturalnyy": ("натураль", "natural"),
    "hani": ("honey", "хани"),
    "fanki": ("anaerob", "ferment", "фанк", "funk"),
    "smes": ("смесь", "blend", "mix"),
    "drugoy": tuple(),
}

COUNTRY_KEYWORDS = {
    "braziliya": ("бразил", "brazil"),
    "efiopiya": ("эфиоп", "ethiopia"),
    "kolumbiya": ("колумб", "colombia"),
    "keniya": ("кения", "kenya"),
    "ruanda": ("руанда", "rwanda"),
    "gvatemala": ("гватемал", "guatemala"),
    "kosta-rika": ("коста-рика", "costa-rica", "costa rica"),
}

ROAST_QUERY_MAP = {
    "light": Q(roast_level="light") | Q(name__icontains="светл"),
    "medium": Q(roast_level="medium"),
    "dark": Q(roast_level="dark") | Q(name__icontains="тёмн") | Q(name__icontains="темн"),
    "dark_for_milk": (
        Q(roast_level="dark_for_milk")
        | Q(roast_level="espresso")
        | Q(name__icontains="батч")
        | Q(name__icontains="mix")
        | Q(processing_method__icontains="смесь")
    ),
}


def _parse_multi_values(request, param_name):
    values = []
    for raw_value in request.GET.getlist(param_name):
        for part in str(raw_value).split(","):
            value = part.strip()
            if value:
                values.append(value)
    deduplicated = []
    seen = set()
    for value in values:
        if value not in seen:
            seen.add(value)
            deduplicated.append(value)
    return deduplicated


def _or_keywords_query(fields, keywords):
    combined = Q()
    for keyword in keywords:
        normalized_keyword = str(keyword).strip()
        if not normalized_keyword:
            continue
        for field in fields:
            combined |= Q(**{f"{field}__icontains": normalized_keyword})
    return combined


def _build_querystring(request, updates=None, remove=None):
    params = request.GET.copy()
    remove = remove or []
    for key in remove:
        params.pop(key, None)
    for key, value in (updates or {}).items():
        params.pop(key, None)
        if value in (None, "", [], ()):
            continue
        if isinstance(value, (list, tuple)):
            prepared = [str(v) for v in value if str(v)]
            if prepared:
                params.setlist(key, prepared)
        else:
            params.setlist(key, [str(value)])
    return params.urlencode()


def _build_pagination_items(current_page, total_pages):
    if total_pages <= 1:
        return []
    if total_pages <= 7:
        return list(range(1, total_pages + 1))
    pages = [1]
    start = max(2, current_page - 1)
    end = min(total_pages - 1, current_page + 1)
    if start > 2:
        pages.append("...")
    pages.extend(range(start, end + 1))
    if end < total_pages - 1:
        pages.append("...")
    pages.append(total_pages)
    return pages


def _available_home_promo(user, now=None):
    """Return the first currently usable promo that the user has not used."""
    from django.utils import timezone
    from apps.orders.models import Order, PromoCode

    now = now or timezone.now()
    used_promo_ids = Order.objects.filter(
        user=user,
        promo_code__isnull=False,
    ).exclude(
        status=Order.STATUS_CANCELLED,
    ).values_list("promo_code_id", flat=True)

    return (
        PromoCode.objects.filter(
            is_active=True,
            valid_from__lte=now,
            valid_to__gte=now,
        )
        .filter(
            Q(usage_limit__isnull=True)
            | Q(usage_limit=0)
            | Q(used_count__lt=F("usage_limit"))
        )
        .exclude(pk__in=used_promo_ids)
        .order_by("pk")
        .first()
    )


def _home_loyalty_offer(user):
    """Return the user's fixed discount (assigned in admin)."""
    from apps.orders.models import Order
    paid_or_fulfilled = Order.objects.filter(user=user).exclude(
        status=Order.STATUS_CANCELLED,
    ).filter(
        Q(payment_status=Order.PAYMENT_STATUS_PAID)
        | Q(status__in=(
            Order.STATUS_PAID,
            Order.STATUS_ASSEMBLING,
            Order.STATUS_SHIPPED,
            Order.STATUS_DELIVERED,
            Order.STATUS_COMPLETED,
        ))
    )
    total_spent = paid_or_fulfilled.aggregate(total=Sum("total_amount"))["total"] or 0
    return {
        "total_spent": total_spent,
        "discount_percent": user.wholesale_discount or 0,
    }


def index(request):
    week_specials = list(
        Product.objects.filter(is_active=True, is_featured=True)
        .filter(category__name__icontains="Кофе")
        .prefetch_related("variants", "flavor_notes", "brew_methods")
        .select_related("category")[:8]
    )
    new_arrivals = list(
        Product.objects.filter(is_active=True, is_new=True)
        .prefetch_related("variants", "flavor_notes")
        .select_related("category")[:8]
    )
    popular = list(
        Product.objects.filter(is_active=True, is_bestseller=True)
        .prefetch_related("variants", "flavor_notes")
        .select_related("category")[:8]
    )

    def _fill_home_products(products, fallback_queryset, limit=8):
        products = list(products)[:limit]
        missing = limit - len(products)
        if missing <= 0:
            return products
        existing_ids = [product.pk for product in products]
        return products + list(fallback_queryset.exclude(pk__in=existing_ids)[:missing])

    if not week_specials:
        week_specials = list(
            Product.objects.filter(is_active=True)
            .filter(category__name__icontains="Кофе")
            .prefetch_related("variants", "flavor_notes")
            .select_related("category")[:8]
        )
    if not new_arrivals:
        new_arrivals = list(
            Product.objects.filter(is_active=True)
            .filter(category__name__icontains="Кофе")
            .prefetch_related("variants", "flavor_notes")
            .select_related("category")[8:16]
        )
    if not popular:
        popular = list(
            Product.objects.filter(is_active=True)
            .filter(category__name__icontains="Кофе")
            .prefetch_related("variants", "flavor_notes")
            .select_related("category")
            .order_by("-rating_avg", "-reviews_count")[:8]
        )

    home_coffee = Product.objects.filter(
        is_active=True,
        category__name__icontains="Кофе",
    ).prefetch_related("variants", "flavor_notes").select_related("category")
    new_arrivals = _fill_home_products(
        new_arrivals,
        home_coffee.order_by("-created_at"),
    )
    popular = _fill_home_products(
        popular,
        home_coffee.order_by("-rating_avg", "-reviews_count", "-created_at"),
    )

    top_categories = Category.objects.filter(
        is_active=True, parent__isnull=True
    ).order_by("order")[:6]

    blog_posts = []
    try:
        from apps.blog.models import BlogPost
        blog_posts = list(BlogPost.objects.filter(is_published=True)[:3])
    except Exception:
        pass

    recent_reviews = list(
        Review.objects.filter(is_approved=True).select_related("user").order_by("-created_at")[:3]
    )
    reviews_count = Review.objects.filter(is_approved=True).count()
    rating_avg = Review.objects.filter(is_approved=True).aggregate(
        avg=Avg("rating")
    )["avg"] or 4.9

    def _trim_for_full_rows(products, specials_count, cols=4):
        products = list(products)
        total = len(products) + specials_count
        full = (total // cols) * cols
        if full <= 0:
            return products
        trim = total - full
        if trim > 0:
            products = products[: max(0, len(products) - trim)]
        return products

    popular = _trim_for_full_rows(popular, 0)
    new_arrivals = _trim_for_full_rows(new_arrivals, 0)

    coffee_count = Product.objects.filter(is_active=True, category__slug='kofe').count()
    accessories_count = Product.objects.filter(is_active=True, category__slug='aksessuary').count()

    espresso_count = Product.objects.filter(
        is_active=True, category__slug='kofe', roast_level='espresso'
    ).count() or Product.objects.filter(
        is_active=True, category__slug='kofe', brew_methods__slug__in=['1b', 'espresso']
    ).distinct().count() or 42
    filter_count = Product.objects.filter(
        is_active=True, category__slug='kofe', roast_level__in=['light', 'medium']
    ).count() or Product.objects.filter(
        is_active=True, category__slug='kofe', brew_methods__slug__in=['3b', 'filter']
    ).distinct().count() or 30

    gift_sets = list(
        Product.objects.filter(is_active=True, category__slug__in=['giftbox', 'nabory'])
        .prefetch_related("variants", "flavor_notes")
        .select_related("category")[:4]
    )
    if not gift_sets:
        gift_sets = list(
            Product.objects.filter(is_active=True)
            .filter(Q(category__name__icontains="Набор") | Q(category__name__icontains="Подароч"))
            .prefetch_related("variants", "flavor_notes")
            .select_related("category")[:4]
        )

    delivery_rating_avg = 4.7
    try:
        dr = Review.objects.filter(is_approved=True).exclude(delivery_rating__isnull=True).aggregate(
            avg=Avg("delivery_rating")
        )["avg"]
        if dr:
            delivery_rating_avg = round(dr, 1)
    except Exception:
        pass

    context = {
        "week_specials": week_specials,
        "new_arrivals": new_arrivals,
        "popular": popular,
        "top_categories": top_categories,
        "blog_posts": blog_posts,
        "recent_reviews": recent_reviews,
        "reviews_count": reviews_count,
        "rating_avg": round(rating_avg, 1),
        "delivery_rating_avg": delivery_rating_avg,
        "home_top_banners": [],
        "home_bottom_banners": [],
        "popular_block_banners": [],
        "new_block_banners": [],
        "coffee_count": coffee_count,
        "espresso_count": espresso_count,
        "filter_count": filter_count,
        "accessories_count": accessories_count,
        "gift_sets": gift_sets,
        "promo_slides": list(PromoSlide.objects.filter(is_active=True).order_by("order")),
    }
    if request.user.is_authenticated:
        from apps.orders.models import Order

        loyalty_offer = _home_loyalty_offer(request.user)
        context.update({
            "has_ordered": Order.objects.filter(user=request.user)
            .exclude(status=Order.STATUS_CANCELLED)
            .exists(),
            "home_promo": _available_home_promo(request.user),
            "home_discount_percent": loyalty_offer["discount_percent"],
            "home_paid_total": loyalty_offer["total_spent"],
        })
    return render(request, "catalog/index.html", context)


def catalog(request, forced_category_slug=None):
    qs = (
        Product.objects.filter(is_active=True)
        .select_related("category")
        .prefetch_related(
            "variants", "variants__grind_type", "variants__roast_type",
            "packagings", "images", "flavor_notes", "brew_methods",
        )
    )

    category_slug = forced_category_slug or request.GET.get("category")
    roast = request.GET.get("roast", "")
    roast_list = [r.strip() for r in roast.split(",") if r.strip()] if roast else []
    search_q = request.GET.get("q", "").strip()
    filter_settings = CatalogFilterSettings.load()
    default_sort = filter_settings.default_sort
    sort = request.GET.get("sort") or default_sort
    methods_raw = request.GET.get("methods", "")
    acidity = request.GET.get("acidity", "")
    acidity_list = [a.strip() for a in acidity.split(",") if a.strip()] if acidity else []
    body_lvl = request.GET.get("body", "")
    body_list = [b.strip() for b in body_lvl.split(",") if b.strip()] if body_lvl else []
    flavor_raw = request.GET.get("flavor", "")
    processing_list = [p.strip() for p in request.GET.getlist("processing") if p.strip()]
    processing = ",".join(processing_list)
    country = request.GET.get("country", "")
    country_list = [c.strip() for c in country.split(",") if c.strip()] if country else []
    features_raw = request.GET.get("features", "")
    qfilter = request.GET.get("qfilter", "")
    bought_before = request.GET.get("bought_before", "")

    current_category_obj = None
    category_trail = []
    if category_slug:
        current_category_obj = Category.objects.filter(slug=category_slug).first()
        if current_category_obj:
            cat_ids = [current_category_obj.id] + list(
                current_category_obj.children.values_list("id", flat=True)
            )
            qs = qs.filter(category_id__in=cat_ids)
            node = current_category_obj
            while node is not None:
                category_trail.insert(0, node)
                node = node.parent
        else:
            qs = qs.filter(category__slug=category_slug)
    if search_q:
        qs = qs.filter(Q(name__icontains=search_q) | Q(short_description__icontains=search_q))

    if methods_raw:
        method_slugs = [m.strip() for m in methods_raw.split(",") if m.strip()]
        if method_slugs:
            qs = qs.filter(brew_methods__slug__in=method_slugs)

    base_qs = qs

    if roast_list:
        qs = qs.filter(roast_level__in=roast_list)

    if acidity_list:
        aq = Q()
        for a in acidity_list:
            if a == "low":
                aq |= Q(acidity__lte=3)
            elif a == "medium":
                aq |= Q(acidity__gte=4, acidity__lte=7)
            elif a == "high":
                aq |= Q(acidity__gte=8)
        qs = qs.filter(aq)

    if body_list:
        bq = Q()
        for b in body_list:
            if b == "low":
                bq |= Q(body__lte=3)
            elif b == "medium":
                bq |= Q(body__gte=4, body__lte=7)
            elif b == "high":
                bq |= Q(body__gte=8)
        qs = qs.filter(bq)

    if flavor_raw:
        flavor_slugs = [f.strip() for f in flavor_raw.split(",") if f.strip()]
        if flavor_slugs:
            qs = qs.filter(flavor_notes__slug__in=flavor_slugs)

    if processing_list:
        pq = Q()
        for p in processing_list:
            pq |= Q(processing_method__iexact=p)
        qs = qs.filter(pq)

    if country_list:
        cq = Q()
        for c in country_list:
            cq |= Q(origin_country__iexact=c)
        qs = qs.filter(cq)

    if features_raw:
        feature_list = [f.strip() for f in features_raw.split(",") if f.strip()]
        fq = Q()
        has_filter = False
        for feat in feature_list:
            if feat == "micro_lot":
                fq |= Q(is_microlot=True)
                has_filter = True
            elif feat == "decaf":
                fq |= Q(caffeine_content__isnull=False, caffeine_content__lt=0.3)
                has_filter = True
            elif feat == "running_out":
                fq |= Q(variants__stock_qty__gt=0, variants__stock_qty__lte=5)
                has_filter = True
            elif feat == "single_origin":
                fq |= Q(origin_country__isnull=False) & ~Q(origin_country="")
                has_filter = True
            elif feat == "for_milk":
                fq |= Q(roast_level="espresso") | Q(roast_level="dark_for_milk")
                has_filter = True
        if has_filter:
            qs = qs.filter(fq)

    qs = apply_situational(qs, qfilter, filter_settings)

    if bought_before and request.user.is_authenticated:
        bought_ids = (
            OrderItem.objects.filter(
                order__user=request.user,
                order__status__in=["paid", "assembling", "shipped", "delivered", "completed"],
                variant__product__isnull=False,
            ).values_list("variant__product_id", flat=True).distinct()
        )
        if bought_before == "yes":
            qs = qs.filter(id__in=bought_ids)
        elif bought_before == "no":
            qs = qs.exclude(id__in=bought_ids)

    allowed_sorts = [
        "-created_at", "created_at",
        "-rating_avg", "rating_avg",
        "-reviews_count", "reviews_count",
    ]
    if sort in ("variants__price", "-variants__price"):
        qs = (
            qs.annotate(_min_price=Min("variants__price"))
            .filter(_min_price__isnull=False)
            .order_by(sort.replace("variants__price", "_min_price"))
        )
    elif sort in allowed_sorts:
        qs = qs.order_by(sort)
    else:
        qs = qs.order_by("-created_at")

    qs = qs.distinct()

    total_count = Product.objects.filter(is_active=True).count()
    filtered_count = qs.count()

    paginator = VariablePaginator(qs, per_page=24, first_page_size=23)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    categories = Category.objects.filter(is_active=True, parent__isnull=True).order_by("order")

    section_category = None
    if current_category_obj is not None:
        section_category = current_category_obj if current_category_obj.parent_id is None else current_category_obj.parent
    if section_category is None:
        section_category = Category.objects.filter(
            is_active=True, slug__in=["kofe", "coffee"]
        ).first()
    if section_category is not None:
        hashtag_categories = list(
            section_category.children.filter(is_active=True).order_by("order", "name")
        )
    else:
        hashtag_categories = list(
            Category.objects.filter(is_active=True, parent__isnull=True).order_by("order")
        )
    featured_hashtag_categories = [c for c in hashtag_categories if c.is_featured]
    hidden_hashtag_categories = [c for c in hashtag_categories if not c.is_featured]

    facets, filters_total = build_facets(qs)

    section_slug = (section_category.slug or "").casefold() if section_category else ""
    section_name = (section_category.name or "").casefold() if section_category else ""
    show_coffee_controls = section_category is None or (
        section_slug in {"kofe", "coffee"} or "кофе" in section_name
    )
    quiz_availability = {}
    if show_coffee_controls:
        quiz_methods = {
            "espresso": "espresso",
            "capsules": "capsules",
            "turka": "turka",
            "filter": "filter",
        }
        taste_filters = {
            "sour": Q(acidity__gte=8, roast_level="light"),
            "bitter": Q(acidity__lte=3, roast_level="dark"),
            "sweet": Q(roast_level="medium"),
            "balanced": Q(acidity__gte=4, acidity__lte=7, roast_level="medium"),
            "rich": Q(body__gte=8, roast_level="dark"),
        }
        for quiz_key, method_slug in quiz_methods.items():
            method_qs = base_qs.filter(brew_methods__slug=method_slug).distinct()
            quiz_availability[quiz_key] = {
                "available": method_qs.exists(),
                "tastes": {
                    taste: method_qs.filter(condition).exists()
                    for taste, condition in taste_filters.items()
                },
            }

    quick_filters = [
        {"id": tab_id, "label": label}
        for tab_id, label in SITUATIONAL_TABS if tab_id
    ]

    is_child_category = bool(current_category_obj and current_category_obj.parent_id)
    has_facet_filters = any([
        is_child_category, roast, search_q, methods_raw, acidity, body_lvl,
        flavor_raw, processing, country, features_raw, bought_before,
    ])
    show_reset_all = bool(qfilter or (sort and sort != default_sort))
    has_any_filters = bool(has_facet_filters or show_reset_all)
    section_reset_url = section_category.get_absolute_url() if section_category else "/catalog/"
    has_active_filters = has_facet_filters

    from apps.orders.models import PromoCode
    from django.utils import timezone
    now = timezone.now()
    active_promo = PromoCode.objects.filter(
        is_active=True, valid_from__lte=now, valid_to__gte=now
    ).first()
    if active_promo and request.user.is_authenticated:
        from apps.orders.models import Order
        if Order.objects.filter(user=request.user).exists():
            active_promo = None
    cart_promo_code = None
    if request.user.is_authenticated:
        cart = getattr(request.user, 'cart', None)
        if cart and cart.promo_code:
            cart_promo_code = cart.promo_code.code

    compatible_cat_ids = set()
    if section_category is not None:
        sec_cat_ids = [section_category.id] + list(section_category.children.values_list("id", flat=True))
        nav_qs = Product.objects.filter(is_active=True, category_id__in=sec_cat_ids)
        if methods_raw:
            method_slugs = [m.strip() for m in methods_raw.split(",") if m.strip()]
            if method_slugs:
                nav_qs = nav_qs.filter(brew_methods__slug__in=method_slugs)
        if search_q:
            nav_qs = nav_qs.filter(Q(name__icontains=search_q) | Q(short_description__icontains=search_q))
        compatible_cat_ids = set(nav_qs.values_list("category_id", flat=True).distinct())

    context = {
        "compatible_cat_ids": compatible_cat_ids,
        "products": page_obj,
        "page_obj": page_obj,
        "paginator": paginator,
        "categories": categories,
        "facets": facets,
        "filters_total": filters_total,
        "quick_filters": quick_filters,
        "current_category": category_slug,
        "current_category_obj": current_category_obj,
        "category_trail": category_trail,
        "current_roast": roast_list,
        "current_sort": sort,
        "search_q": search_q,
        "current_methods": [m.strip() for m in methods_raw.split(",") if m.strip()] if methods_raw else [],
        "current_acidity": acidity_list,
        "current_body": body_list,
        "current_flavor": [f.strip() for f in flavor_raw.split(",") if f.strip()] if flavor_raw else [],
        "current_processing": processing_list,
        "current_country": country_list,
        "current_features": [f.strip() for f in features_raw.split(",") if f.strip()] if features_raw else [],
        "current_qfilter": qfilter,
        "current_bought_before": bought_before,
        "current_params": request.GET.copy(),
        "filtered_count": filtered_count,
        "total_count": total_count,
        "has_active_filters": has_active_filters,
        "has_facet_filters": has_facet_filters,
        "has_any_filters": has_any_filters,
        "show_reset_all": show_reset_all,
        "section_reset_url": section_reset_url,
        "default_sort": default_sort,
        "povodyr_dismissed": request.session.get("povodyr_dismissed", False),
        "featured_hashtag_categories": featured_hashtag_categories,
        "hidden_hashtag_categories": hidden_hashtag_categories,
        "active_promo": active_promo,
        "cart_promo_code": cart_promo_code,
        "is_child_category": is_child_category,
        "show_coffee_controls": show_coffee_controls,
        "quiz_availability": quiz_availability,
    }
    if request.GET.get("partial") == "items":
        return render(request, "catalog/partials/product_list_items.html", context)
    if request.htmx:
        hx_target = request.headers.get("HX-Target", "")
        if hx_target == "catalog-content":
            return render(request, "catalog/partials/product_list.html", context)
    return render(request, "catalog/catalog.html", context)


def product_detail(request, slug):
    product = get_object_or_404(
        Product.objects.prefetch_related(
            "variants", "variants__grind_type", "variants__roast_type", "packagings",
            "images", "flavor_notes", "brew_methods",
            "related_products__variants", "related_products__flavor_notes",
            "related_products__packagings",
        ).select_related("category"),
        slug=slug,
        is_active=True,
    )
    reviews = product.reviews.filter(is_approved=True).order_by("-created_at")[:10]
    brewing_methods = list(product.brew_methods.all())

    _track_product_view(request, product)

    from apps.orders.models import PromoCode, Order
    from django.utils import timezone
    now = timezone.now()
    active_promo = PromoCode.objects.filter(
        is_active=True, valid_from__lte=now, valid_to__gte=now
    ).first()
    if active_promo and request.user.is_authenticated:
        if Order.objects.filter(user=request.user).exists():
            active_promo = None

    cart_promo_code = None
    if request.user.is_authenticated:
        cart = getattr(request.user, 'cart', None)
        if cart and cart.promo_code:
            cart_promo_code = cart.promo_code.code

    site_settings = SiteSettings.load()
    cafes = Cafe.objects.filter(is_active=True).order_by("order")[:20]

    context = {
        "product": product,
        "primary_image": product.primary_image,
        "reviews": reviews,
        "brewing_methods": brewing_methods,
        "active_promo": active_promo,
        "cart_promo_code": cart_promo_code,
        "site_settings": site_settings,
        "cafes": cafes,
    }
    return render(request, "catalog/detail.html", context)


def _track_product_view(request, product):
    """Записать просмотр товара (1.6) с дедупом ~6 ч на сессию."""
    from datetime import timedelta
    from django.utils import timezone
    from .models import ProductView

    if not request.session.session_key:
        request.session.save()
    session_key = request.session.session_key or ""

    recently = ProductView.objects.filter(
        product=product,
        session_key=session_key,
        created_at__gte=timezone.now() - timedelta(hours=6),
    ).exists()
    if not recently:
        ProductView.objects.create(product=product, session_key=session_key)


def compare_view(request):
    ids_str = request.GET.get("ids", "")
    ids = [int(x) for x in ids_str.split(",") if x.strip().isdigit()]
    seen = set()
    ordered_ids = []
    for pid in ids:
        if pid not in seen:
            seen.add(pid)
            ordered_ids.append(pid)
    ordered_ids = ordered_ids[:4]

    products = list(
        Product.objects.filter(id__in=ordered_ids, is_active=True)
        .select_related("category")
        .prefetch_related("variants", "flavor_notes")
    )
    products.sort(key=lambda p: ordered_ids.index(p.id) if p.id in ordered_ids else len(ordered_ids))

    def _min_price(product):
        prices = [
            (v.effective_price or v.price)
            for v in product.variants.all()
            if (v.effective_price or v.price)
        ]
        return min(prices) if prices else None

    rows = []
    if products:
        def add_row(label, values, kind="text"):
            normalized = [("" if v in (None, "") else str(v)) for v in values]
            differs = len(set(normalized)) > 1
            rows.append({
                "label": label,
                "values": values,
                "kind": kind,
                "differs": differs,
            })

        add_row("Цена от", [_min_price(p) for p in products], kind="price")
        add_row("Рейтинг", [p.rating_avg for p in products], kind="rating")
        add_row("Обжарка", [p.get_roast_level_display() or "—" for p in products])
        add_row("Обработка", [p.processing_method or "—" for p in products])
        add_row("Страна", [p.origin_country or "—" for p in products])
        add_row("Регион", [p.region or "—" for p in products])
        add_row("Высота", [p.altitude or "—" for p in products])
        add_row("Q-оценка", [p.q_score or "—" for p in products])
        add_row("Кофеин, %", [p.caffeine_content or "—" for p in products])
        add_row("Плотность", [p.body for p in products], kind="scale")
        add_row("Кислотность", [p.acidity for p in products], kind="scale")
        add_row("Сладость", [p.sweetness for p in products], kind="scale")
        add_row("Вкусовые нотки", [p.flavor_notes_list or "—" for p in products])

    context = {
        "products": products,
        "ids": ordered_ids,
        "rows": rows,
        "can_add_more": len(products) < 4,
        "has_any_diff": any(row["differs"] for row in rows),
    }
    return render(request, "catalog/compare.html", context)


SECTION_SLUG_ALIASES = {
    "coffee": "kofe",
    "tea": "chay",
    "accessories": "aksessuary",
}


def _resolve_category_slug(slug):
    """Вернуть реальный slug категории (с учётом алиасов) или None."""
    if not slug:
        return None
    candidate = SECTION_SLUG_ALIASES.get(slug, slug)
    if Category.objects.filter(slug=candidate).exists():
        return candidate
    if Category.objects.filter(slug=slug).exists():
        return slug
    return None


def coffee_node(request, slug):
    """Диспетчер /coffee/<slug>/ — ЧПУ конфликт раздела «Кофе»."""
    coffee = Category.objects.filter(slug__in=["kofe", "coffee"], parent__isnull=True).first()
    if coffee is not None:
        child = Category.objects.filter(slug=slug, parent=coffee, is_active=True).first()
        if child is not None:
            return catalog(request, forced_category_slug=child.slug)
    return product_detail(request, slug)


def section_catalog(request, section, child=None):
    """1.4.7 — ЧПУ страницы раздела/категории."""
    from django.shortcuts import render

    target = child or section
    resolved = _resolve_category_slug(target)
    if resolved is None:
        return render(request, "404.html", status=404)

    if child is not None:
        section_resolved = _resolve_category_slug(section)
        child_cat = Category.objects.filter(slug=resolved).select_related("parent").first()
        if (
            section_resolved is None
            or child_cat is None
            or child_cat.parent is None
            or child_cat.parent.slug != section_resolved
        ):
            return render(request, "404.html", status=404)

    return catalog(request, forced_category_slug=resolved)


def category_redirect(request, category_slug):
    """Совместимость: bare /<slug>/ -> рендер каталога раздела/категории."""
    from django.shortcuts import render
    resolved = _resolve_category_slug(category_slug)
    if resolved is None:
        return render(request, "404.html", status=404)
    return catalog(request, forced_category_slug=resolved)


def search_suggest(request):
    """Autocomplete endpoint: groups by Каталог and Журнал."""
    query = (request.GET.get("q") or "").strip()
    scope = (request.GET.get("scope") or "").strip().lower()
    if scope not in {"catalog", "blog"}:
        scope = ""
    if len(query) < 2:
        return JsonResponse({"products": [], "posts": [], "query": query, "scope": scope})

    product_results = []
    if scope != "blog":
        products = list(
            Product.objects.filter(is_active=True)
            .filter(Q(name__icontains=query) | Q(short_description__icontains=query))
            .select_related("category")
            .prefetch_related("variants")[:6]
        )
        for p in products:
            image = ""
            try:
                if p.main_image:
                    image = p.main_image.url
            except Exception:
                pass
            min_price = None
            variants = p.variants.all()
            if variants:
                min_price = str(min(v.price for v in variants))
            product_results.append({
                "id": p.id,
                "name": p.name,
                "url": f"/coffee/{p.slug}/",
                "category": p.category.name if p.category else "",
                "image": image,
                "price": min_price,
            })

    post_results = []
    if scope != "catalog":
        try:
            from apps.blog.models import BlogPost
            posts = list(
                BlogPost.objects.filter(is_published=True)
                .filter(Q(title__icontains=query) | Q(short_description__icontains=query))[:6]
            )
            for post in posts:
                image = ""
                try:
                    if post.image:
                        image = post.image.url
                except (ValueError, OSError):
                    pass
                post_results.append({
                    "id": post.id,
                    "title": post.title,
                    "url": f"/blog/{post.slug}/",
                    "image": image,
                })
        except Exception:
            pass

    return JsonResponse({
        "query": query,
        "scope": scope,
        "products": product_results,
        "posts": post_results,
    })


@require_POST
def dismiss_povodyr(request):
    request.session["povodyr_dismissed"] = True
    return JsonResponse({"ok": True})


def cafe_list_api(request):
    """API: список точек продаж для товара (3.9)."""
    slug = request.GET.get("product")
    if not slug:
        return JsonResponse({"cafes": []})
    cafes = Cafe.objects.filter(is_active=True, products__slug=slug).order_by("order")
    data = [{
        "id": c.id,
        "name": c.name,
        "address": c.address,
        "city": c.city,
        "lat": float(c.latitude),
        "lng": float(c.longitude),
        "phone": c.phone,
        "working_hours": c.working_hours,
        "description": c.description,
    } for c in cafes]
    return JsonResponse({"cafes": data})