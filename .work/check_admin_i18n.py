from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.utils.translation import gettext, override

from apps.catalog.models import Product, SiteSettings


with override("ru"):
    print(f"RECURRING_ADMIN_SWITCH|{SiteSettings.load().recurring_payments_enabled}")
    for source in (
        "Search apps and models...",
        "Select action",
        "Type to search",
    ):
        print(f"GETTEXT|{source}|{gettext(source)}")

    request = RequestFactory().get("/admin/catalog/product/")
    request.user = get_user_model().objects.filter(is_superuser=True).first()
    if request.user is None:
        request.user = get_user_model().objects.create_superuser(
            username="admin-i18n-check",
            email="admin-i18n-check@example.invalid",
            password=None,
        )
    response = admin.site._registry[Product].changelist_view(request)
    response.render()
    html = response.content.decode("utf-8")

    for source in (
        "Search apps and models...",
        "Select action",
        "Type to search",
    ):
        print(f"HTML_ENGLISH|{source}|{source in html}")

    for expected in (
        "Поиск по приложениям и моделям...",
        "Выберите действие",
        "Введите для поиска",
    ):
        print(f"HTML_RUSSIAN|{expected}|{expected in html}")
