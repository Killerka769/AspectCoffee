"""Ситуативные фильтры каталога (ТЗ 1.6).

Каждая ситуация (верхний таб каталога) превращает queryset товаров в суженный
queryset согласно управляемым из админки порогам `CatalogFilterSettings`.
"""
from datetime import timedelta

from django.db.models import Count, Exists, OuterRef, Q, Sum
from django.utils import timezone


# Период «новизны» -> кол-во дней.
NEW_PERIOD_DAYS = {
    "day": 1,
    "week": 7,
    "decade": 10,
    "month": 30,
    "quarter": 91,
    "halfyear": 182,
    "year": 365,
}

# Список табов для рендера в шаблоне (id -> подпись).
SITUATIONAL_TABS = [
    ("", "Все"),
    ("recommended", "Рекомендуем"),
    ("popular", "Популярный"),
    ("new", "Новый"),
    ("week", "Сорт недели"),
    ("ending", "Заканчивается"),
    ("bestseller", "Хит продаж"),
    ("micro", "Микролот"),
]


def apply_situational(qs, qfilter, settings):
    """Сузить queryset товаров согласно выбранному ситуативному фильтру.

    qs       — queryset Product (уже отфильтрованный по разделу/категории и фасетам)
    qfilter  — строковый id таба (см. SITUATIONAL_TABS)
    settings — экземпляр CatalogFilterSettings (CatalogFilterSettings.load())
    """
    from apps.catalog.models import ProductVariant
    from apps.orders.models import Order, OrderItem

    now = timezone.now()

    if not qfilter or qfilter == "all":
        return qs

    if qfilter == "recommended":
        return qs.filter(is_featured=True)

    if qfilter == "micro":
        return qs.filter(is_microlot=True)

    if qfilter == "new":
        days = NEW_PERIOD_DAYS.get(settings.new_period, 7)
        return qs.filter(created_at__gte=now - timedelta(days=days))

    if qfilter == "popular":
        # Просмотры всего ≥ порога.
        return (
            qs.annotate(_views_total=Count("views", distinct=True))
            .filter(_views_total__gte=settings.popular_views_threshold)
        )

    if qfilter == "week":
        # Просмотры за последние 7 дней ≥ порога.
        week_ago = now - timedelta(days=7)
        return (
            qs.annotate(
                _views_week=Count(
                    "views", filter=Q(views__created_at__gte=week_ago), distinct=True
                )
            )
            .filter(_views_week__gte=settings.week_special_views_threshold)
        )

    if qfilter == "ending":
        # «Заканчивается»: КАЖДЫЙ вариант упаковки имеет остаток ≤ порога.
        # => нет ни одного варианта с остатком > порога, и хотя бы один вариант существует.
        threshold = settings.ending_stock_threshold
        has_variant = ProductVariant.objects.filter(product=OuterRef("pk"))
        has_above = ProductVariant.objects.filter(
            product=OuterRef("pk"), stock_qty__gt=threshold
        )
        return (
            qs.annotate(_has_variant=Exists(has_variant), _has_above=Exists(has_above))
            .filter(_has_variant=True, _has_above=False)
        )

    if qfilter == "bestseller":
        # Продаж (Σ qty) в завершённых заказах за период ≥ порога.
        period_start = now - timedelta(days=settings.bestseller_period_days)
        sold = (
            OrderItem.objects.filter(
                variant__product=OuterRef("pk"),
                order__status=Order.STATUS_COMPLETED,
                order__created_at__gte=period_start,
            )
            .values("variant__product")
            .annotate(total=Sum("qty"))
            .values("total")
        )
        # Подзапрос вернёт NULL, если продаж не было — оборачиваем через annotate+filter.
        from django.db.models import Subquery, IntegerField
        from django.db.models.functions import Coalesce
        return (
            qs.annotate(
                _sold=Coalesce(
                    Subquery(sold, output_field=IntegerField()), 0
                )
            )
            .filter(_sold__gte=settings.bestseller_sales_threshold)
        )

    return qs
