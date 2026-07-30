"""
CDEK API endpoints for the checkout page.

All views return JSON and are called by the frontend (Alpine.js).
No authentication required (public checkout).
"""
import json
import logging

from django.core.cache import cache
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt

from .cdek import CDEKClient

logger = logging.getLogger(__name__)

HEADER_CITIES = (
    "Москва",
    "Санкт-Петербург",
    "Екатеринбург",
    "Казань",
    "Новосибирск",
    "Краснодар",
    "Нижний Новгород",
    "Самара",
    "Уфа",
    "Ростов-на-Дону",
)


@require_GET
def cdek_cities(request):
    """
    GET /api/cdek/cities/?q=Моск
    Returns list of matching cities.
    """
    query = (request.GET.get("q") or "").strip()
    if len(query) < 2:
        return JsonResponse({"cities": []})

    client = CDEKClient()
    if not client.configured():
        return JsonResponse({"error": "СДЭК не настроен"}, status=503)

    cities = client.search_cities(query, limit=10)
    return JsonResponse({"cities": cities})


@require_GET
def cdek_offices(request):
    """
    GET /api/cdek/offices/?city_code=44
    Returns list of PVZ/offices for a given city.
    """
    city_code = request.GET.get("city_code")
    if not city_code:
        return JsonResponse({"error": "city_code обязателен"}, status=400)

    try:
        city_code = int(city_code)
    except (ValueError, TypeError):
        return JsonResponse({"error": "city_code должен быть числом"}, status=400)

    client = CDEKClient()
    if not client.configured():
        return JsonResponse({"error": "СДЭК не настроен"}, status=503)

    offices = client.get_offices(city_code, pvz_type="PVZ")
    return JsonResponse({"offices": offices})


@require_GET
def cdek_pvz_count(request):
    """
    GET /api/cdek/pvz-count/ — all CDEK points in Russia.
    GET /api/cdek/pvz-count/?city=Москва — points in the selected city.
    """
    requested_city = (request.GET.get("city") or "Россия").strip()
    if requested_city.casefold() == "россия":
        requested_city = "Россия"
    elif requested_city not in HEADER_CITIES:
        return JsonResponse({"error": "Город недоступен для выбора"}, status=400)

    cache_key = f"cdek:pvz-count:{requested_city.casefold()}"
    cached = cache.get(cache_key)
    if cached is not None:
        return JsonResponse(cached)

    client = CDEKClient()
    if not client.configured():
        return JsonResponse({"error": "СДЭК не настроен"}, status=503)

    city_code = None
    if requested_city != "Россия":
        matches = client.search_cities(requested_city, limit=10)
        exact_matches = [
            city for city in matches
            if city.get("city", "").casefold() == requested_city.casefold()
            and city.get("country", "").casefold() == "россия"
        ]
        if not exact_matches:
            return JsonResponse({"error": "Город не найден в СДЭК"}, status=404)
        city_code = exact_matches[0].get("code")

    count = client.get_office_count(city_code=city_code, country_code="RU")
    if count is None:
        return JsonResponse({"error": "СДЭК временно недоступен"}, status=503)

    payload = {
        "city": requested_city,
        "city_code": city_code,
        "count": count,
    }
    cache.set(cache_key, payload, timeout=12 * 60 * 60)
    return JsonResponse(payload)


@csrf_exempt
@require_POST
def cdek_calc(request):
    """
    POST /api/cdek/calc/
    Body JSON: {city_code: int, delivery_type: "cdek_pvz"|"cdek_door", weight: int (grams)}
    Returns delivery cost and days.
    """
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Некорректный JSON"}, status=400)

    city_code = data.get("city_code")
    delivery_type = data.get("delivery_type", "cdek_pvz")
    weight = data.get("weight", 500)  # default 500g
    street = (data.get("street") or "").strip()
    house = (data.get("house") or "").strip()
    postal_code = (data.get("postal_code") or "").strip()

    if not city_code:
        return JsonResponse({"error": "city_code обязателен"}, status=400)

    try:
        city_code = int(city_code)
        weight = max(int(weight), 100)  # minimum 100g
    except (ValueError, TypeError):
        return JsonResponse({"error": "Некорректные данные"}, status=400)

    client = CDEKClient()
    if not client.configured():
        return JsonResponse({"error": "СДЭК не настроен"}, status=503)

    to_address = street
    if to_address and house:
        to_address += f", д. {house}"

    result = client.calc_delivery_cost(
        to_city_code=city_code,
        weight_grams=weight,
        delivery_type=delivery_type,
        to_address=to_address or None,
        to_postal_code=postal_code or None,
    )

    if "error" in result:
        return JsonResponse({"error": result["error"]}, status=400)

    return JsonResponse({
        "cost": float(result["cost"]),
        "period_min": result["period_min"],
        "period_max": result["period_max"],
        "tariff_name": result["tariff_name"],
    })
