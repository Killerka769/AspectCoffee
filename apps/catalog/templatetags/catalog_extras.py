import re
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

FLAVOR_COLORS = {
    "тёмного винограда": "#6c0e53",
    "красного яблока": "#c70000",
    "тёмного шоколада": "#5A3A22",
    "вишни": "#B22222",
    "абрикоса": "#ffc08a",
    "белого винограда": "#e5e7c6",
    "чёрного чая": "#8b4513",
    "малинового варенья": "#c41e3a",
    "персика": "#ffdab9",
    "голубики": "#4b0082",
    "цветочного мёда": "#daa520",
    "жареных орехов": "#8B6914",
    "печенья": "#d2a679",
    "нуги": "#c9a96e",
    "шоколада": "#6B3A2A",
    "карамели": "#c07838",
    "тёмных ягод": "#4a0e4e",
    "цитрусов": "#ff8c00",
    "молочного шоколада": "#8B5E3C",
    "тёмной карамели": "#7B3F00",
    "цукатов": "#d2691e",
    "специй": "#8B4513",
    "арахиса": "#d2b48c",
    "пудры какао": "#6B3A2A",
    "цедры лимона": "#e8d44d",
    "ореховой пасты": "#8B6914",
    "изюма": "#6B3A2A",
    "апельсина": "#ff8c00",
    "сухофруктов": "#8B6914",
    "цветов": "#fffcd1",
    "чернослива": "#4c0a4d",
    "грейпфрута": "#ff6347",
    "жёлтых фруктов": "#ffd700",
    "спелого лимона": "#fff44f",
    "тростникового сахара": "#a67c52",
    "лайма": "#32cd32",
    "клубники": "#ff4757",
    "смородины": "#8b0000",
    "инжира": "#8B4513",
    "груши": "#d3d3a4",
    "ананаса": "#ffd700",
    "манго": "#ffb347",
    "бергамота": "#d4e157",
    "жасмина": "#f8f8ff",
    "лаванды": "#e6e6fa",
    "розы": "#ff69b4",
    "гибискуса": "#c41e3a",
    "кедровых орехов": "#7b3f00",
    "фундука": "#d2b48c",
    "миндаля": "#ffe4b5",
    "сливок": "#fffdd0",
    "сливочного масла": "#fff8dc",
    "солёной карамели": "#c07838",
    "кленового сиропа": "#c07838",
    "тёмной патоку": "#3c1414",
    "табака": "#8b4513",
    "вишнёвой косточки": "#800000",
    "сухого вина": "#722f37",
    "портвейна": "#722f37",
    "рождественской выпечки": "#d2a679",
}

def _text_color(bg_hex):
    r = int(bg_hex[1:3], 16)
    g = int(bg_hex[3:5], 16)
    b = int(bg_hex[5:7], 16)
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return "#000000" if luminance > 0.5 else "#ffffff"


@register.filter
def get_item(dict_obj, key):
    return dict_obj.get(key, "")


@register.filter
def ru_plural(value, forms):
    """Russian 3-form pluralization: {{ n|ru_plural:"сорт,сорта,сортов" }}.
    Handles the 11-14 exception (always the 'many' form)."""
    try:
        n = abs(int(value))
    except (TypeError, ValueError):
        return ""
    one, few, many = [f.strip() for f in forms.split(",")]
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not (12 <= n % 100 <= 14):
        return few
    return many


@register.filter(is_safe=True)
def colorize_flavors(html):
    if not html:
        return ""
    for flavor, bg in FLAVOR_COLORS.items():
        tc = _text_color(bg)
        html = re.sub(
            re.escape(flavor),
            f'<span class="descriptor-badge" style="background:{bg};color:{tc}">{flavor}</span>',
            html,
            flags=re.IGNORECASE,
        )
    return mark_safe(html)
