"""
CDEK API v2 client for Aspect Coffee.

Handles: authentication, city search, office/PVZ listing,
tariff calculation, order creation, order tracking.
"""
from __future__ import annotations

import logging
import time
from decimal import Decimal
from typing import Any

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)


def _sender_city_code() -> int | None:
    raw = getattr(settings, "CDEK_SENDER_CITY_CODE", "")
    try:
        code = int(str(raw).strip())
    except (TypeError, ValueError):
        return None
    return code or None


def _sender_address() -> str:
    return str(getattr(settings, "CDEK_SENDER_ADDRESS", "") or "").strip()


# Tariff codes for online-shop (type=1, from warehouse)
TARIFF_WAREHOUSE_TO_PVZ = 136       # склад → склад (ПВЗ)
TARIFF_WAREHOUSE_TO_DOOR = 137      # склад → дверь
TARIFF_WAREHOUSE_TO_POSTAMAT = 368  # склад → постамат

# Default package dimensions (cm) for coffee shipments
DEFAULT_LENGTH = 30
DEFAULT_WIDTH = 20
DEFAULT_HEIGHT = 15


class CDEKClient:
    """Client for CDEK API v2."""

    def __init__(self):
        from django.core.exceptions import ImproperlyConfigured
        from urllib.parse import urlsplit

        default_url = "https://api.edu.cdek.ru/v2" if getattr(settings, "CDEK_TEST_MODE", False) else "https://api.cdek.ru/v2"
        raw_url = (getattr(settings, "CDEK_API_URL", "") or default_url).rstrip("/")
        endpoint = urlsplit(raw_url)
        if endpoint.scheme != "https" or endpoint.username or endpoint.password or endpoint.query or endpoint.fragment or endpoint.path not in ("", "/v2"):
            raise ImproperlyConfigured("CDEK_API_URL must be an HTTPS API root without credentials or query parameters")
        if getattr(settings, "CDEK_TEST_MODE", False) and endpoint.hostname == "api.cdek.ru":
            raise ImproperlyConfigured("CDEK_TEST_MODE=True conflicts with the live CDEK_API_URL")
        if not getattr(settings, "CDEK_TEST_MODE", False) and endpoint.hostname == "api.edu.cdek.ru":
            raise ImproperlyConfigured("Set CDEK_TEST_MODE=True for the sandbox CDEK_API_URL")
        # Normalize: strip /v2 suffix if present — we add it per-endpoint
        if raw_url.endswith("/v2"):
            raw_url = raw_url[:-3]
        self.base_url = raw_url + "/v2"
        self.client_id = (getattr(settings, "CDEK_CLIENT_ID", "") or "").strip()
        self.client_secret = (getattr(settings, "CDEK_CLIENT_SECRET", "") or "").strip()
        self._token: str | None = None
        self._token_expires: float = 0

    # ── Auth ────────────────────────────────────────────────

    def configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def _get_token(self) -> str | None:
        if not self.configured():
            logger.warning("СДЭК: CDEK_CLIENT_ID / CDEK_CLIENT_SECRET не заданы.")
            return None
        if self._token and time.time() < self._token_expires:
            return self._token
        try:
            with httpx.Client(timeout=30.0) as client:
                r = client.post(
                    f"{self.base_url}/oauth/token",
                    data={
                        "grant_type": "client_credentials",
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                    },
                )
                r.raise_for_status()
                data = r.json()
                self._token = data["access_token"]
                self._token_expires = time.time() + data.get("expires_in", 3500) - 60
                return self._token
        except Exception as exc:
            logger.error("СДЭК: ошибка получения токена: %s", exc)
            return None

    def _headers(self) -> dict[str, str]:
        token = self._get_token()
        if not token:
            return {}
        return {"Authorization": f"Bearer {token}"}

    # ── Cities ──────────────────────────────────────────────

    def search_cities(self, query: str, limit: int = 10) -> list[dict]:
        """Search cities by name. Returns list of {code, city, region, country}."""
        if not self.configured():
            return []
        try:
            with httpx.Client(timeout=15.0) as client:
                r = client.get(
                    f"{self.base_url}/location/cities",
                    params={"city": query, "country_codes": "RU", "size": limit},
                    headers=self._headers(),
                )
                r.raise_for_status()
                return [
                    {
                        "code": c.get("code"),
                        "city": c.get("city", ""),
                        "region": c.get("region", ""),
                        "country": c.get("country", ""),
                    }
                    for c in r.json()
                ]
        except Exception as exc:
            logger.error("СДЭК: ошибка поиска городов: %s", exc)
            return []

    # ── Offices / PVZ ───────────────────────────────────────

    def get_offices(self, city_code: int, pvz_type: str = "ALL") -> list[dict]:
        """
        Get delivery points (PVZ/postamats) for a city.
        pvz_type: PVZ, POSTAMAT, ALL
        """
        if not self.configured():
            return []
        try:
            params: dict[str, Any] = {"city_code": city_code}
            if pvz_type != "ALL":
                params["type"] = pvz_type
            with httpx.Client(timeout=20.0) as client:
                r = client.get(
                    f"{self.base_url}/deliverypoints",
                    params=params,
                    headers=self._headers(),
                )
                r.raise_for_status()
                results = []
                for p in r.json():
                    loc = p.get("location", {})
                    results.append({
                        "code": p.get("code", ""),
                        "name": p.get("name", ""),
                        "address": loc.get("address_full") or loc.get("address", ""),
                        "city": loc.get("city", ""),
                        "latitude": loc.get("latitude"),
                        "longitude": loc.get("longitude"),
                        "work_time": p.get("work_time", ""),
                        "type": p.get("type", ""),
                        "have_cashless": p.get("have_cashless", False),
                        "have_cash": p.get("have_cash", False),
                        "is_dressing_room": p.get("is_dressing_room", False),
                        "phone": (p.get("phones") or [{}])[0].get("number", "") if p.get("phones") else "",
                    })
                return results
        except Exception as exc:
            logger.error("СДЭК: ошибка получения ПВЗ: %s", exc)
            return []

    def get_office_count(
        self,
        city_code: int | None = None,
        country_code: str = "RU",
    ) -> int | None:
        """Return the number of CDEK PVZ/postamats for a city or country."""
        if not self.configured():
            return None
        try:
            params: dict[str, Any] = {
                "country_code": country_code,
                "type": "ALL",
            }
            if city_code is not None:
                params["city_code"] = city_code
            with httpx.Client(timeout=60.0) as client:
                r = client.get(
                    f"{self.base_url}/deliverypoints",
                    params=params,
                    headers=self._headers(),
                )
                r.raise_for_status()
                data = r.json()
                return len(data) if isinstance(data, list) else None
        except Exception as exc:
            logger.error("СДЭК: ошибка подсчёта ПВЗ: %s", exc)
            return None

    # ── Tariff calculation ──────────────────────────────────

    def calc_tariff(
        self,
        to_city_code: int,
        weight_grams: int,
        tariff_code: int | None = None,
        from_city_code: int | None = None,
        to_address: str | None = None,
        to_postal_code: str | None = None,
    ) -> dict[str, Any]:
        """
        Calculate delivery cost for a specific tariff.
        Returns {delivery_sum, period_min, period_max, tariff_code, tariff_name, ...}
        """
        if not self.configured():
            return {"error": "CDEK не настроен"}
        if from_city_code is None:
            from_city_code = _sender_city_code()
        if not from_city_code:
            return {"error": "Город отправления СДЭК не задан"}
        packages = [{
            "weight": weight_grams,
            "length": DEFAULT_LENGTH,
            "width": DEFAULT_WIDTH,
            "height": DEFAULT_HEIGHT,
        }]
        to_location: dict[str, Any] = {"code": to_city_code}
        if to_address:
            to_location["address"] = to_address
        if to_postal_code:
            to_location["postal_code"] = to_postal_code
        payload: dict[str, Any] = {
            "type": 1,
            "from_location": {"code": from_city_code},
            "to_location": to_location,
            "packages": packages,
        }
        if tariff_code:
            payload["tariff_code"] = tariff_code
        try:
            with httpx.Client(timeout=15.0) as client:
                endpoint = "calculator/tariff" if tariff_code else "calculator/tarifflist"
                r = client.post(
                    f"{self.base_url}/{endpoint}",
                    json=payload,
                    headers=self._headers(),
                )
                r.raise_for_status()
                return r.json()
        except Exception as exc:
            logger.error("СДЭК: ошибка расчёта тарифа: %s", exc)
            return {"error": str(exc)}

    def calc_delivery_cost(
        self,
        to_city_code: int,
        weight_grams: int,
        delivery_type: str,
        to_address: str | None = None,
        to_postal_code: str | None = None,
    ) -> dict[str, Any]:
        """
        Calculate delivery cost based on delivery type.
        delivery_type: 'cdek_pvz' or 'cdek_door'
        Returns: {cost: Decimal, period_min: int, period_max: int, tariff_name: str}
        """
        tariff_code = (
            TARIFF_WAREHOUSE_TO_PVZ if delivery_type == "cdek_pvz"
            else TARIFF_WAREHOUSE_TO_DOOR
        )
        result = self.calc_tariff(
            to_city_code=to_city_code,
            weight_grams=weight_grams,
            tariff_code=tariff_code,
            to_address=to_address,
            to_postal_code=to_postal_code,
        )
        if "error" in result:
            return result
        if "errors" in result:
            return {"error": result["errors"][0].get("message", "Ошибка расчёта")}
        return {
            "cost": Decimal(str(result.get("delivery_sum", 0))),
            "period_min": result.get("period_min", 0),
            "period_max": result.get("period_max", 0),
            "tariff_code": tariff_code,
            "tariff_name": result.get("tariff_name", ""),
            "total_sum": result.get("total_sum", result.get("delivery_sum", 0)),
            "currency": result.get("currency", "RUB"),
        }

    # ── Order creation ──────────────────────────────────────

    def create_order(self, order) -> dict[str, Any]:
        """Create a real CDEK order with full payload."""
        if not self.configured():
            return {"error": "CDEK не настроен"}
        city_code = _sender_city_code()
        if not city_code:
            return {"error": "Город отправления СДЭК не задан"}

        tariff_code = (
            TARIFF_WAREHOUSE_TO_PVZ if order.delivery_type == "cdek_pvz"
            else TARIFF_WAREHOUSE_TO_DOOR
        )

        # Build items list from order
        items = []
        total_weight = 0
        for item in order.items.all():
            weight = 0
            if item.variant and item.variant.weight:
                weight = int(item.variant.weight) * item.qty
            else:
                weight = 300 * item.qty  # default 300g per item
            total_weight += weight
            items.append({
                "name": item.product_name[:120],
                "ware_key": str(item.variant_id or item.pk),
                "payment": {"value": 0},  # prepaid
                "cost": float(item.price_at_order),
                "weight": weight,
                "amount": item.qty,
            })

        if total_weight < 100:
            total_weight = 300  # minimum

        # Build payload
        payload: dict[str, Any] = {
            "type": 1,  # internet-shop
            "number": str(order.pk),
            "tariff_code": tariff_code,
            "comment": f"Заказ #{order.pk} — Aspect Coffee",
            "sender": {
                "name": "Aspect Coffee",
                "phones": [{"number": "+79999999999"}],  # placeholder
            },
            "recipient": {
                "name": order.delivery_recipient_name or "Получатель",
                "phones": [{"number": order.delivery_recipient_phone or ""}],
                "email": order.contact_email or "",
            },
            "from_location": {
                "code": city_code,
                **({"address": _sender_address()} if _sender_address() else {}),
            },
            "packages": [{
                "number": f"PKG-{order.pk}",
                "weight": total_weight,
                "length": DEFAULT_LENGTH,
                "width": DEFAULT_WIDTH,
                "height": DEFAULT_HEIGHT,
                "items": items,
            }],
        }

        # Set destination based on delivery type
        if order.delivery_type == "cdek_pvz" and order.cdek_pvz_code:
            payload["delivery_point"] = order.cdek_pvz_code
        else:
            # Door delivery — need address
            addr = order.delivery_address or {}
            city = addr.get("city", "")
            street = addr.get("street", "")
            house = addr.get("house", "")
            apartment = addr.get("apartment", "")
            postal_code = addr.get("postal_code", "")
            full_address = street
            if house:
                full_address += f", д. {house}"
            if apartment:
                full_address += f", кв. {apartment}"
            payload["to_location"] = {
                "address": full_address,
                "city": city,
            }
            if postal_code:
                payload["to_location"]["postal_code"] = postal_code
            # Try to resolve city code from cdek
            if city:
                cities = self.search_cities(city, limit=1)
                if cities:
                    payload["to_location"]["code"] = cities[0]["code"]

        try:
            with httpx.Client(timeout=60.0) as client:
                r = client.post(
                    f"{self.base_url}/orders",
                    json=payload,
                    headers=self._headers(),
                )
                r.raise_for_status()
                data = r.json()
                logger.info("СДЭК: заказ #%s создан, uuid=%s", order.pk, data.get("entity", {}).get("uuid"))
                return data
        except httpx.HTTPStatusError as exc:
            error_body = exc.response.json() if exc.response.content else {}
            logger.error("СДЭК: create_order HTTP %s: %s", exc.response.status_code, error_body)
            return {"error": str(error_body), "status_code": exc.response.status_code}
        except Exception as exc:
            logger.error("СДЭК: create_order ошибка: %s", exc)
            return {"error": str(exc)}

    # ── Order tracking ──────────────────────────────────────

    def get_order(self, uuid: str) -> dict[str, Any]:
        """Get order info by CDEK UUID."""
        if not self.configured():
            return {}
        try:
            with httpx.Client(timeout=30.0) as client:
                r = client.get(
                    f"{self.base_url}/orders/{uuid}",
                    headers=self._headers(),
                )
                r.raise_for_status()
                return r.json()
        except Exception as exc:
            logger.error("СДЭК: get_order %s ошибка: %s", uuid, exc)
            return {}

    def calc_tariff_preview(
        self,
        *,
        from_location: dict[str, Any],
        to_location: dict[str, Any],
        packages: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Preview tariff calculations (dummy API response/compat)."""
        if not self.configured():
            return {"detail": "CDEK credentials not configured", "total_sum": None}
        return {"detail": "Use CDEK calculator endpoint in production", "total_sum": None}
