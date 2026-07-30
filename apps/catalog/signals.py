"""Сигналы каталога.

Поддерживают денормализованные Product.reviews_count и Product.rating_avg
в актуальном состоянии при создании/изменении/удалении отзывов (ТЗ 2.2:
счётчик «Отзывы» должен отражать реальное число одобренных отзывов).
"""
from django.db.models import Avg, Count
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver


def recompute_product_reviews(product_id):
    """Пересчитать reviews_count и rating_avg по одобренным отзывам товара."""
    from apps.catalog.models import Product, Review
    if not product_id:
        return
    agg = Review.objects.filter(product_id=product_id, is_approved=True).aggregate(
        avg=Avg("rating"), count=Count("id"),
    )
    Product.objects.filter(pk=product_id).update(
        rating_avg=round(agg["avg"], 2) if agg["avg"] is not None else 0,
        reviews_count=agg["count"] or 0,
    )


@receiver(post_save, sender="catalog.Review")
def review_saved(sender, instance, **kwargs):
    recompute_product_reviews(instance.product_id)


@receiver(post_delete, sender="catalog.Review")
def review_deleted(sender, instance, **kwargs):
    recompute_product_reviews(instance.product_id)


# --- Фикс поиска: SQLite LIKE регистронезависимый только для ASCII. ---
# Для кириллицы («флорал» vs «Флорал») переопределяем функцию LIKE на
# Python-реализацию с Unicode-insensitive сравнением. PostgreSQL (prod)
# не затрагивается — там icontains работает корректно из коробки.
import re as _re

from django.db.backends.signals import connection_created
from django.dispatch import receiver as _receiver


def _sqlite_like_unicode(pattern, value):
    if pattern is None or value is None:
        return False
    # re.escape (Py>=3.7) не экранирует % и _ — заменяем их напрямую.
    regex = _re.escape(str(pattern)).replace("%", ".*").replace("_", ".")
    return _re.fullmatch(regex, str(value), _re.IGNORECASE | _re.DOTALL) is not None


@_receiver(connection_created)
def _patch_sqlite_like(sender, connection, **kwargs):
    if connection.vendor == "sqlite":
        connection.connection.create_function("LIKE", 2, _sqlite_like_unicode)
        # Django добавляет ESCAPE '\\' => SQLite вызывает 3-аргументную like().
        connection.connection.create_function(
            "LIKE", 3, lambda pat, val, esc: _sqlite_like_unicode(pat, val)
        )
