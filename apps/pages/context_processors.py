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


def site_chrome(request):
    ctx = {
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