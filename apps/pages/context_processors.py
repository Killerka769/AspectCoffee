"""Context processor exposing admin-managed pages models (banners, site links, compare count)
to all templates so the navbar/footer/home page can render them without per-view changes.
"""

def site_chrome(request):
    ctx = {
        "footer_links_company": [],
        "footer_links_help": [],
        "footer_links_catalog": [],
        "promo_links": {},
        "compare_count": 0,
        "site_settings": None,
    }
    try:
        from .models import SiteLink
        all_links = list(SiteLink.objects.filter(is_active=True).order_by("group", "order", "label"))
        for link in all_links:
            if link.group == "footer_company":
                ctx["footer_links_company"].append(link)
            elif link.group == "footer_help":
                ctx["footer_links_help"].append(link)
            elif link.group == "footer_catalog":
                ctx["footer_links_catalog"].append(link)
            elif link.group == "promo":
                ctx["promo_links"][link.label] = link
    except Exception:
        pass
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
