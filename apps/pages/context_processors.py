"""Context processor exposing admin-managed pages models to all templates."""


def _active_popup(request):
    path = request.path or "/"
    if path.startswith("/admin"):
        return None
    if path in ("/", ""):
        place = "home"
    elif path == "/catalog" or path.startswith("/catalog/"):
        place = "catalog"
    else:
        place = ""
    try:
        from django.db.utils import OperationalError, ProgrammingError
        from apps.pages.models import PopupMessage

        active = PopupMessage.objects.filter(is_active=True)
        if place:
            chosen = active.filter(show_on_pages=place).order_by("-updated_at").first()
            if chosen:
                return chosen
        return active.filter(show_on_pages=PopupMessage.ShowOn.ALL).order_by("-updated_at").first()
    except (OperationalError, ProgrammingError):
        return None


def _page_banners(request):
    path = request.path or "/"
    if path in ("/", ""):
        page = "home"
    elif path == "/catalog" or path.startswith("/catalog/"):
        page = "catalog"
    elif path == "/blog" or path == "/blog/" or path.startswith("/blog/category/"):
        page = "journal"
    else:
        return []
    try:
        from django.db.utils import OperationalError, ProgrammingError
        from apps.pages.models import PageBanner

        return list(
            PageBanner.objects.filter(is_active=True, page=page).order_by("order", "id")
        )
    except (OperationalError, ProgrammingError):
        return []


def _seo_breadcrumbs(request):
    """Хлебные крошки для JSON-LD. Карточка товара и статья подменяют блок в шаблоне."""
    path = request.path or "/"
    crumbs = [{"name": "Главная", "path": "/"}]
    if path in ("/", ""):
        return crumbs
    sections = (
        ("/catalog", "Каталог"),
        ("/coffee", "Кофе"),
        ("/tea", "Чай"),
        ("/chocolate", "Шоколад"),
        ("/accessories", "Аксессуары"),
        ("/giftbox", "Подарочные наборы"),
        ("/blog", "Журнал"),
        ("/reviews", "Отзывы"),
        ("/community", "Сообщество"),
        ("/reels", "Шортсы"),
        ("/faq", "FAQ"),
        ("/how-to-choose-coffee", "Как выбрать кофе"),
        ("/shipment-and-payment", "Доставка и оплата"),
        ("/discount-system", "Система скидок"),
        ("/return-money", "Возврат денег"),
        ("/coffee-in-office", "Кофе в офис"),
        ("/contact-us", "Контакты"),
        ("/partners", "Партнёрам"),
        ("/about", "О компании"),
        ("/privacy", "Политика конфиденциальности"),
        ("/user-agreement", "Пользовательское соглашение"),
        ("/public-offer", "Публичная оферта"),
        ("/sitemap", "Карта сайта"),
    )
    for prefix, name in sections:
        if path == prefix or path == prefix + "/" or path.startswith(prefix + "/"):
            crumbs.append({"name": name, "path": prefix + "/"})
            break
    return crumbs


def site_chrome(request):
    ctx = {
        "seo_breadcrumbs": _seo_breadcrumbs(request),
        "footer_links_company": [],
        "footer_links_help": [],
        "footer_links_catalog": [],
        "promo_links": {},
        "compare_count": 0,
        "site_settings": None,
        "active_popup": _active_popup(request),
        "page_banners": _page_banners(request),
    }
    # SiteLink model was removed — footer links are now hardcoded in the template.
    try:
        from apps.catalog.models import SiteSettings
        ctx["site_settings"] = SiteSettings.load()
    except Exception:
        pass
    # compare count is client-side (localStorage), but we accept a cookie hint if present
    try:
        raw = request.COOKIES.get("tc_compare_count")
        if raw and raw.isdigit():
            ctx["compare_count"] = int(raw)
    except Exception:
        pass
    return ctx