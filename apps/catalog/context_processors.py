"""Контекст-процессоры каталога.

nav_sections — разделы верхнего меню «Купить» (ТЗ 1.4.2): корневые категории из БД,
чтобы меню строилось из админки, а не было захардкожено в шаблоне.

nav_menu_items — дополнительные произвольные пункты меню «Купить»,
управляемые через модель NavMenuItem в Django Admin.
"""


def nav_sections(request):
    sections = []
    menu_items = []
    try:
        from .models import Category, NavMenuItem
        sections = list(
            Category.objects.filter(parent__isnull=True, is_active=True)
            .exclude(slug__in=["subscription", "podpiska", "podpiska-na-kofe"])
            .exclude(name__icontains="подпис")
            .order_by("order", "name")
        )
        menu_items = list(
            NavMenuItem.objects.filter(is_active=True).order_by("order", "title")
        )
    except Exception:
        pass
    return {"nav_sections": sections, "nav_menu_items": menu_items}


def published_reviews_count(request):
    """Возвращает количество опубликованных отзывов для счётчика в шапке."""
    count = 0
    try:
        from .models import Review
        count = Review.objects.filter(is_approved=True).count()
    except Exception:
        pass
    return {"published_reviews_count": count}
