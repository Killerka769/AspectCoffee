"""Динамические фасеты фильтрации (ТЗ 1.4.5 / 1.4.6).

build_facets(base_qs) строит набор опций фильтра ТОЛЬКО из товаров текущего
раздела/категории. Любая опция, которая дала бы 0 товаров, не попадает в результат.
Так гарантируется: кол-во условий фильтрации на странице = реальные свойства
товаров этого раздела/категории.
"""
from django.db.models import Count, Exists, OuterRef, Q


# Диапазоны для шкальных свойств (значение 0..10).
ACIDITY_RANGES = [
    ("low", "Низкая", Q(acidity__lte=3)),
    ("medium", "Средняя", Q(acidity__gte=4, acidity__lte=7)),
    ("high", "Высокая", Q(acidity__gte=8)),
]
BODY_RANGES = [
    ("low", "Лёгкое", Q(body__lte=3)),
    ("medium", "Среднее", Q(body__gte=4, body__lte=7)),
    ("high", "Насыщенное", Q(body__gte=8)),
]

# Особенности кофе: id -> (подпись, условие Q).
def _feature_conditions():
    return [
        ("blend", "Смесь", Q(tags__slug="blend")),
        ("decaf", "Без кофеина",
         Q(caffeine_content__isnull=False, caffeine_content__lt=0.3) | Q(tags__slug="decaf")),
        ("single_origin", "Моносорт", Q(tags__slug="single-origin")),
        ("micro_lot", "Микролот", Q(is_microlot=True)),
        ("for_milk", "Для молока", Q(tags__slug="for-milk")),
        ("limited", "Лимитированный", Q(tags__slug="limited")),
    ]


def _roast_label(value):
    from apps.catalog.models import Product
    return dict(Product.ROAST_CHOICES).get(value, value)


def _normalized_text_facet(base_qs, field_name):
    """Group a free-text field using Unicode-aware, DB-independent casing."""
    groups = {}
    rows = (
        base_qs.exclude(**{field_name: ""})
        .values_list("id", field_name)
        .distinct()
        .order_by(field_name, "id")
    )
    for product_id, raw_value in rows:
        display_value = str(raw_value or "").strip()
        if not display_value:
            continue
        normalized_value = display_value.casefold()
        group = groups.setdefault(
            normalized_value,
            {"value": display_value, "name": display_value, "product_ids": set()},
        )
        group["product_ids"].add(product_id)

    return [
        {
            "value": group["value"],
            "name": group["name"],
            "count": len(group["product_ids"]),
        }
        for _, group in sorted(groups.items())
    ]


def build_facets(base_qs):
    """Вернуть dict фасетов и общее число опций (filters_total).

    base_qs — queryset активных товаров, суженный ТОЛЬКО по разделу/категории
    (и поиску), но до применения самих фасетных фильтров.

    Возвращает: (facets: dict, filters_total: int)
    Каждая непустая группа -> список dict {value/slug, label/name, count}.
    Пустые группы в dict не попадают.
    """
    from apps.catalog.models import BrewMethod, FlavorNote

    facets = {}

    # ---- Способы приготовления (brew_methods, M2M) ----
    methods = list(
        BrewMethod.objects.filter(product__in=base_qs)
        .annotate(count=Count("product", filter=Q(product__in=base_qs), distinct=True))
        .filter(count__gt=0)
        .order_by("name")
        .values("slug", "name", "count")
    )
    if methods:
        facets["methods"] = methods

    # ---- Вкусовые нотки (flavor_notes, M2M) ----
    flavors = list(
        FlavorNote.objects.filter(product__in=base_qs)
        .annotate(count=Count("product", filter=Q(product__in=base_qs), distinct=True))
        .filter(count__gt=0)
        .order_by("name")
        .values("slug", "name", "count")
    )
    if flavors:
        facets["flavor"] = flavors

    # ---- Степень обжарки (CharField с choices) ----
    roast_rows = (
        base_qs.exclude(roast_level="")
        .values("roast_level")
        .annotate(count=Count("id"))
        .order_by("roast_level")
    )
    roast = [
        {"value": r["roast_level"], "name": _roast_label(r["roast_level"]), "count": r["count"]}
        for r in roast_rows if r["count"] > 0
    ]
    if roast:
        facets["roast"] = roast

    # ---- Способ обработки (free-text CharField) ----
    # The parser historically stored the same value with different casing
    # (for example ``Смесь`` and ``смесь``).  The catalog filters with
    # ``iexact``, therefore the facet must use the same normalization or its
    # displayed count will disagree with the result count.
    processing = _normalized_text_facet(base_qs, "processing_method")
    if processing:
        facets["processing"] = processing

    # ---- Страна произрастания (free-text CharField) ----
    country = _normalized_text_facet(base_qs, "origin_country")
    if country:
        facets["country"] = country

    # ---- Кислотность (диапазоны) ----
    acidity = []
    for value, name, cond in ACIDITY_RANGES:
        cnt = base_qs.filter(cond).count()
        if cnt > 0:
            acidity.append({"value": value, "name": name, "count": cnt})
    if acidity:
        facets["acidity"] = acidity

    # ---- Плотность (диапазоны) ----
    body = []
    for value, name, cond in BODY_RANGES:
        cnt = base_qs.filter(cond).count()
        if cnt > 0:
            body.append({"value": value, "name": name, "count": cnt})
    if body:
        facets["body"] = body

    # ---- Особенности кофе ----
    features = []
    for value, name, cond in _feature_conditions():
        cnt = base_qs.filter(cond).distinct().count()
        if cnt > 0:
            features.append({"value": value, "name": name, "count": cnt})
    if features:
        facets["features"] = features

    filters_total = sum(len(options) for options in facets.values())
    return facets, filters_total
