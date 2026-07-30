
import json
import logging
import hmac
import hashlib
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.views import View
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.throttling import AnonRateThrottle

from apps.orders.models import Order
from apps.payments.models import Payment
from apps.payments.services import (
    apply_verified_payment,
    fetch_yookassa_payment,
    verified_payment_values,
)

logger = logging.getLogger(__name__)


class PaymentWebhookThrottle(AnonRateThrottle):
    rate = "60/minute"


@method_decorator(csrf_exempt, name="dispatch")
class PaymentWebhookView(APIView):
    """
    YooKassa webhook endpoint.
    Idempotency: yookassa_id unique=True + select_for_update().
    Race condition fix: get_or_create instead of get — webhook may arrive
    before CreatePaymentView writes to DB.
    """
    permission_classes = [permissions.AllowAny]
    throttle_classes = [PaymentWebhookThrottle]

    def post(self, request):
        data = request.data
        if not data and request.body:
            try:
                data = json.loads(request.body)
            except (json.JSONDecodeError, UnicodeDecodeError):
                return Response({"detail": "Invalid JSON"}, status=status.HTTP_400_BAD_REQUEST)

        event = data.get("event", "")
        obj = data.get("object", {})
        payment_id = obj.get("id", "")

        if not payment_id:
            return Response({"ok": True})  # Ignore malformed

        # SECURITY (CWE-345): never trust the webhook body. A forged
        # payment.succeeded POST must NOT be able to mark an order paid.
        # Fetch the authoritative payment object from the YooKassa API and use
        # ITS status / amount / metadata as the source of truth. Mirrors the
        # balance-topup webhook (apps/users/yookassa_views.py).
        shop_id = getattr(settings, "YOOKASSA_SHOP_ID", "")
        secret_key = getattr(settings, "YOOKASSA_SECRET_KEY", "")
        if not shop_id or not secret_key:
            logger.error("YooKassa webhook: payment credentials not configured")
            return Response({"detail": "unavailable"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        try:
            verified = fetch_yookassa_payment(payment_id)
        except Exception as e:
            # Unknown/forged id, or transient API error -> do NOT mutate state.
            logger.warning(f"YooKassa webhook: cannot verify payment {payment_id} via API: {e}")
            return Response({"ok": True})

        values = verified_payment_values(verified)
        verified_status = values["status"]
        verified_order_id = values["order_id"]
        verified_amount = values["amount"]

        logger.info(
            f"YooKassa webhook: event={event} payment_id={payment_id} "
            f"api_status={verified_status} order_id={verified_order_id}"
        )

        try:
            return self._process_webhook(
                payment_id,
                verified_status,
                verified_order_id,
                verified_amount,
                values["saved_payment_method_id"],
                values["payment_method_saved"],
                values["payment_method_type"],
                values["card_last4"],
            )
        except Exception as e:
            logger.error(f"Webhook processing error: {e}")
            return Response({"detail": "Processing error"}, status=status.HTTP_400_BAD_REQUEST)

    def _process_webhook(
        self,
        payment_id,
        verified_status,
        order_id,
        verified_amount,
        saved_payment_method_id="",
        payment_method_saved=False,
        payment_method_type="",
        card_last4="",
    ):
        apply_verified_payment(
            payment_id,
            verified_status,
            order_id,
            verified_amount,
            saved_payment_method_id,
            payment_method_saved,
            payment_method_type,
            card_last4,
        )
        return Response({"ok": True})

class CreatePaymentView(APIView):
    """Create a YooKassa payment for an order."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        order_id = request.data.get("order_id")
        order = get_object_or_404(Order, id=order_id, user=request.user)

        if order.payment_status == Order.PAYMENT_STATUS_PAID:
            return Response(
                {"detail": "Заказ уже оплачен"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        shop_id = getattr(settings, "YOOKASSA_SHOP_ID", "")
        secret_key = getattr(settings, "YOOKASSA_SECRET_KEY", "")
        if not shop_id or not secret_key:
            return Response(
                {"detail": "Платёжная система временно недоступна"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        try:
            import yookassa
            yookassa.Configuration.account_id = shop_id
            yookassa.Configuration.secret_key = secret_key

            import uuid
            idempotency_key = str(uuid.uuid4())

            payment_payload = {
                "amount": {
                    "value": str(order.total_amount),
                    "currency": "RUB",
                },
                "confirmation": {
                    "type": "redirect",
                    "return_url": request.build_absolute_uri(
                        reverse("orders:order_success", args=[order.id])
                    ),
                },
                "capture": True,
                "description": f"Заказ #{order.id} — Aspect Coffee",
                "metadata": {"order_id": str(order.id)},
            }
            recurring_plan = getattr(order, "recurring_plan", None)
            if recurring_plan and recurring_plan.status == recurring_plan.STATUS_PENDING:
                payment_payload["save_payment_method"] = True
                payment_payload["merchant_customer_id"] = str(order.user_id)

            payment_data = yookassa.Payment.create(payment_payload, idempotency_key)

            payment, _ = Payment.objects.get_or_create(
                order=order,
                defaults={
                    "yookassa_id": payment_data.id,
                    "amount": order.total_amount,
                    "status": Payment.STATUS_PENDING,
                    "confirmation_url": payment_data.confirmation.confirmation_url,
                },
            )
            if payment.yookassa_id != payment_data.id:
                payment.yookassa_id = payment_data.id
                payment.confirmation_url = payment_data.confirmation.confirmation_url
                payment.save(update_fields=["yookassa_id", "confirmation_url"])
            if order.payment_id != payment_data.id:
                order.payment_id = payment_data.id
                order.save(update_fields=["payment_id"])

            from apps.payments.tasks import check_payment_timeout
            from apps.catalog.models import SiteSettings
            site_settings = SiteSettings.load()
            timeout_minutes = site_settings.payment_timeout_minutes or 10
            check_payment_timeout.apply_async(
                args=[payment.id],
                countdown=timeout_minutes * 60,
            )

            return Response({
                "payment_id": payment_data.id,
                "confirmation_url": payment_data.confirmation.confirmation_url,
            })

        except Exception as e:
            logger.error(f"YooKassa create payment error for order #{order_id}: {e}")
            return Response(
                {"detail": "Ошибка при создании платежа. Попробуйте позже."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class InitiateRefundView(APIView):
    """Initiate YooKassa refund for an order (staff only)."""
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, order_id):
        order = get_object_or_404(Order, id=order_id)

        if not hasattr(order, "payment") or order.payment.status != Payment.STATUS_SUCCEEDED:
            return Response(
                {"detail": "Нет успешного платежа для возврата"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from apps.payments.tasks import process_refund
        process_refund.delay(order.id)

        return Response({"detail": "Запрос на возврат принят в обработку"})
