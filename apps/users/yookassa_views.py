import json
import logging
import uuid
import hashlib
import hmac
from decimal import Decimal, InvalidOperation
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.views import View
from yookassa import Configuration, Payment
from apps.users.models import PaymentTransaction, User

logger = logging.getLogger(__name__)


class YookassaPaymentView(View):
    """View to initialize Yookassa payment for balance top-up."""
    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Authentication required"}, status=401)

        try:
            data = json.loads(request.body)
            amount = data.get("amount")
            if not amount:
                return JsonResponse({"error": "Amount is required"}, status=400)

            try:
                amount = Decimal(str(amount))
            except (InvalidOperation, ValueError):
                return JsonResponse({"error": "Invalid amount"}, status=400)

            if amount < 100:
                return JsonResponse({"error": "Minimum top-up amount is 100 RUB"}, status=400)
            if amount > 100000:
                return JsonResponse({"error": "Maximum top-up amount is 100,000 RUB"}, status=400)

            Configuration.account_id = settings.YOOKASSA_SHOP_ID
            Configuration.secret_key = settings.YOOKASSA_SECRET_KEY

            idempotency_key = str(uuid.uuid4())
            payment = Payment.create({
                "amount": {
                    "value": str(amount),
                    "currency": "RUB"
                },
                "confirmation": {
                    "type": "redirect",
                    "return_url": request.build_absolute_uri("/account/balance/")
                },
                "capture": True,
                "description": f"Пополнение баланса: {request.user.email}",
                "metadata": {
                    "user_id": str(request.user.id)
                }
            }, idempotency_key)

            PaymentTransaction.objects.create(
                user=request.user,
                payment_id=payment.id,
                amount=amount,
                status="pending",
                provider="yookassa"
            )

            return JsonResponse({"confirmation_url": payment.confirmation.confirmation_url})

        except Exception as e:
            logger.error(f"Yookassa init error: {str(e)}")
            return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def yookassa_webhook(request):
    """
    Handle YooKassa webhook for balance top-up payment confirmation.

    Security features:
    1. Idempotency check - prevent double crediting
    2. Atomic operations with select_for_update
    3. Amount verification against our records
    4. Validates payment via YooKassa API before crediting
    """
    try:
        event_json = json.loads(request.body)

        event = event_json.get("event", "")
        obj = event_json.get("object", {})
        payment_id = obj.get("id", "")
        payment_status = obj.get("status", "")

        if not payment_id:
            logger.warning("Webhook received without payment_id")
            return HttpResponse(status=200)

        logger.info(f"YooKassa balance webhook: event={event}, payment_id={payment_id}, status={payment_status}")

        # Only process successful payments
        if event != "payment.succeeded" or payment_status != "succeeded":
            logger.info(f"Ignoring non-success event: {event}")
            return HttpResponse(status=200)

        # Configure YooKassa to verify payment via API
        Configuration.account_id = settings.YOOKASSA_SHOP_ID
        Configuration.secret_key = settings.YOOKASSA_SECRET_KEY

        # Fetch fresh payment data directly from YooKassa API
        payment_data = Payment.find_one(payment_id)

        if payment_data.status != "succeeded":
            logger.warning(f"Payment {payment_id} not yet succeeded in YooKassa API")
            return HttpResponse(status=200)

        # Use atomic transaction with select_for_update to prevent race conditions
        with transaction.atomic():
            try:
                # Lock the transaction row to prevent concurrent processing
                tx = PaymentTransaction.objects.select_for_update().get(payment_id=payment_id)

                # IDEMPOTENCY CHECK: If already completed, skip (prevent double crediting)
                if tx.status == "completed":
                    logger.info(f"Payment {payment_id} already processed (idempotency check passed)")
                    return HttpResponse(status=200)

                # SECURITY: Verify amount matches our records (prevent amount tampering)
                if float(payment_data.amount.value) != float(tx.amount):
                    logger.error(
                        f"SECURITY ALERT: Amount mismatch for payment {payment_id}. "
                        f"Expected {tx.amount}, got {payment_data.amount.value}"
                    )
                    return HttpResponse(status=400)

                # Lock the user row and update balance atomically
                user = User.objects.select_for_update().get(id=tx.user_id)
                user.balance += tx.amount
                user.save(update_fields=["balance", "updated_at"])

                # Mark transaction as completed
                tx.status = "completed"
                tx.completed_at = timezone.now()
                tx.save(update_fields=["status", "completed_at", "updated_at"])

                logger.info(f"Balance credited: user={user.id}, +{tx.amount} RUB, payment={payment_id}")

            except PaymentTransaction.DoesNotExist:
                logger.warning(f"Payment transaction not found in DB: {payment_id}")

        return HttpResponse(status=200)

    except json.JSONDecodeError:
        logger.error("Invalid JSON in webhook request")
        return HttpResponse(status=400)
    except Exception as e:
        logger.error(f"YooKassa balance webhook error: {str(e)}")
        return HttpResponse(status=500)
