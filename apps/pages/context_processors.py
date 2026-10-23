"""Context processor exposing admin-managed pages models to all templates."""


def site_chrome(request):
    ctx = {
        "footer_links_company": [],
        "footer_links_help": [],
        "footer_links_catalog": [],
        "promo_links": {},
        "compare_count": 0,
        "site_settings": None,
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