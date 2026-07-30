"""Самопроверка 1.4.6: ни одна опция фильтра не должна давать 0 товаров.

Для каждого раздела/категории строим фасеты (build_facets) и проверяем, что
КАЖДАЯ показанная опция при применении к базовому queryset даёт >= 1 товар.
"""
from django.core.management.base import BaseCommand
from django.db.models import Q

from apps.catalog.models import Category, Product
from apps.catalog.facets import build_facets


FEATURE_Q = {
    "blend": Q(tags__slug="blend"),
    "decaf": Q(caffeine_content__isnull=False, caffeine_content__lt=0.3) | Q(tags__slug="decaf"),
    "single_origin": Q(tags__slug="single-origin"),
    "micro_lot": Q(is_microlot=True),
    "for_milk": Q(tags__slug="for-milk"),
    "limited": Q(tags__slug="limited"),
}
ACIDITY_Q = {"low": Q(acidity__lte=3), "medium": Q(acidity__gte=4, acidity__lte=7), "high": Q(acidity__gte=8)}
BODY_Q = {"low": Q(body__lte=3), "medium": Q(body__gte=4, body__lte=7), "high": Q(body__gte=8)}


def _base_qs(category):
    qs = Product.objects.filter(is_active=True)
    cat_ids = [category.id] + list(category.children.values_list("id", flat=True))
    return qs.filter(category_id__in=cat_ids)


def _apply(qs, group, value):
    if group == "methods":
        return qs.filter(brew_methods__slug=value)
    if group == "flavor":
        return qs.filter(flavor_notes__slug=value)
    if group == "roast":
        return qs.filter(roast_level=value)
    if group == "processing":
        return qs.filter(processing_method__iexact=value)
    if group == "country":
        return qs.filter(origin_country__iexact=value)
    if group == "acidity":
        return qs.filter(ACIDITY_Q[value])
    if group == "body":
        return qs.filter(BODY_Q[value])
    if group == "features":
        return qs.filter(FEATURE_Q[value])
    return qs


class Command(BaseCommand):
    help = "1.4.6 — проверить, что ни одна опция фильтра не даёт 0 товаров."

    def handle(self, *args, **options):
        categories = Category.objects.filter(is_active=True).order_by("parent_id", "order")
        total_bad = 0
        for cat in categories:
            base = _base_qs(cat)
            if not base.exists():
                continue
            facets, filters_total = build_facets(base)
            bad = []
            for group, options in facets.items():
                for opt in options:
                    value = opt.get("slug") or opt.get("value")
                    cnt = _apply(base, group, value).distinct().count()
                    if cnt < 1:
                        bad.append(f"{group}={value}")
            status = "OK" if not bad else f"НАРУШЕНИЕ: {bad}"
            total_bad += len(bad)
            self.stdout.write(
                f"{cat.slug:30} товаров={base.count():4} опций={filters_total:3} {status}"
            )
        if total_bad == 0:
            self.stdout.write(self.style.SUCCESS("1.4.6 OK: все опии фильтрации дают >= 1 товар"))
        else:
            self.stdout.write(self.style.ERROR(f"1.4.6 НАРУШЕНО: {total_bad} опций дают 0"))
