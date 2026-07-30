import logging
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.orders.models import Order

from .models import Payment


logger = logging.getLogger(__name__)


def fetch_yookassa_payment(payment_id):
    """Return the authoritative payment object from YooKassa."""
    shop_id = getattr(settings, "YOOKASSA_SHOP_ID", "")
    secret_key = getattr(settings, "YOOKASSA_SECRET_KEY", "")
    if not shop_id or not secret_key:
        raise RuntimeError("YooKassa credentials are not configured")

    from yookassa import Configuration, Payment as YooPayment

    Configuration.account_id = shop_id
    Configuration.secret_key = secret_key
    return YooPayment.find_one(payment_id)


def verified_payment_values(verified):
    metadata = getattr(verified, "metadata", None) or {}
    order_id = metadata.get("order_id")
    try:
        order_id = int(order_id) if order_id else None
    except (TypeError, ValueError):
        order_id = None
    try:
        amount = Decimal(str(verified.amount.value))
    except (AttributeError, InvalidOperation, TypeError):
        amount = None
    payment_method = getattr(verified, "payment_method", None)
    method_id = getattr(payment_method, "id", "") or ""
    method_saved = bool(getattr(payment_method, "saved", False))
    method_type = getattr(payment_method, "type", "") or ""
    card = getattr(payment_method, "card", None)
    card_last4 = getattr(card, "last4", "") or ""
    return {
        "payment_id": getattr(verified, "id", "") or "",
        "status": getattr(verified, "status", "") or "",
        "order_id": order_id,
        "amount": amount,
        "saved_payment_method_id": method_id if method_saved else "",
        "payment_method_saved": method_saved,
        "payment_method_type": method_type,
        "card_last4": card_last4,
    }


def apply_verified_payment(
    payment_id,
    verified_status,
    order_id,
    verified_amount,
    saved_payment_method_id="",
    payment_method_saved=False,
    payment_method_type="",
    card_last4="",
):
    """Apply a status obtained directly from YooKassa, idempotently."""
    result = {
        "payment_id": payment_id,
        "verified_status": verified_status,
        "order_id": order_id,
        "updated": False,
        "order_status_changed": False,
        "reason": "",
    }

    if not payment_id:
        result["reason"] = "missing_payment_id"
        return result

    notify_status = None
    create_waybill = False

    with transaction.atomic():
        payment = Payment.objects.select_for_update().filter(yookassa_id=payment_id).first()
        if payment is None and order_id:
            payment = Payment.objects.select_for_update().filter(order_id=order_id).first()
            if payment is not None:
                if payment.yookassa_id and payment.yookassa_id != payment_id:
                    result["reason"] = "payment_id_mismatch"
                    return result
                payment.yookassa_id = payment_id
                payment.save(update_fields=["yookassa_id", "updated_at"])
        if payment is None:
            if not order_id:
                result["reason"] = "missing_order_id"
                return result
            payment = Payment.objects.create(
                order_id=order_id,
                yookassa_id=payment_id,
                amount=verified_amount or Decimal("0"),
                status=Payment.STATUS_PENDING,
            )

        if order_id and payment.order_id and payment.order_id != order_id:
            result["reason"] = "order_id_mismatch"
            return result
        if not payment.order_id and order_id:
            payment.order_id = order_id
            payment.save(update_fields=["order_id", "updated_at"])

        order = Order.objects.select_for_update().filter(pk=payment.order_id).first()
        if order is None:
            result["reason"] = "order_not_found"
            return result

        if verified_amount is None or verified_amount != order.total_amount:
            logger.error(
                "YooKassa amount mismatch for payment %s / order #%s: %s != %s",
                payment_id,
                order.pk,
                verified_amount,
                order.total_amount,
            )
            result["reason"] = "amount_mismatch"
            return result

        result["order_id"] = order.pk
        if verified_status == "succeeded":
            payment_fields = []
            payment_changed = payment.status != Payment.STATUS_SUCCEEDED
            if payment_changed:
                payment.status = Payment.STATUS_SUCCEEDED
                payment.amount = verified_amount
                payment_fields.extend(["status", "amount"])
            payment_updates = {
                "saved_payment_method_id": saved_payment_method_id if payment_method_saved else "",
                "payment_method_saved": bool(payment_method_saved),
                "payment_method_type": payment_method_type,
                "card_last4": card_last4,
            }
            for field, value in payment_updates.items():
                if getattr(payment, field) != value:
                    setattr(payment, field, value)
                    payment_fields.append(field)
            if payment_fields:
                payment.save(update_fields=[*payment_fields, "updated_at"])

            order_fields = []
            was_paid = order.payment_status == Order.PAYMENT_STATUS_PAID
            if not was_paid:
                order.payment_status = Order.PAYMENT_STATUS_PAID
                order_fields.append("payment_status")
            if order.payment_id != payment_id:
                order.payment_id = payment_id
                order_fields.append("payment_id")
            if order.status in (Order.STATUS_NEW, Order.STATUS_CANCELLED) and not was_paid:
                order.status = Order.STATUS_PAID
                order_fields.append("status")
                result["order_status_changed"] = True
                notify_status = Order.STATUS_PAID
                create_waybill = order.delivery_type in (
                    Order.DELIVERY_CDEK_PVZ,
                    Order.DELIVERY_CDEK_DOOR,
                )
            if order_fields:
                order.save(update_fields=order_fields)

            from datetime import timedelta
            from apps.orders.models import RecurringCharge, RecurringOrder

            recurring_plan = RecurringOrder.objects.select_for_update().filter(
                source_order=order,
                status=RecurringOrder.STATUS_PENDING,
            ).first()
            if recurring_plan:
                if payment_method_saved and saved_payment_method_id:
                    recurring_plan.saved_payment_method_id = saved_payment_method_id
                    recurring_plan.status = RecurringOrder.STATUS_ACTIVE
                    recurring_plan.next_charge_at = timezone.now() + timedelta(
                        weeks=recurring_plan.interval_weeks
                    )
                    recurring_plan.last_error = ""
                    recurring_plan.save(update_fields=[
                        "saved_payment_method_id", "status", "next_charge_at",
                        "last_error", "updated_at",
                    ])
                else:
                    recurring_plan.status = RecurringOrder.STATUS_PAUSED
                    recurring_plan.last_error = (
                        "ЮKassa не подтвердила сохранение способа оплаты. "
                        "Автоповтор не активирован."
                    )
                    recurring_plan.save(update_fields=["status", "last_error", "updated_at"])

            recurring_charge = RecurringCharge.objects.select_for_update().filter(order=order).first()
            if recurring_charge and recurring_charge.status != RecurringCharge.STATUS_SUCCEEDED:
                recurring_charge.status = RecurringCharge.STATUS_SUCCEEDED
                recurring_charge.error_message = ""
                recurring_charge.save(update_fields=["status", "error_message", "updated_at"])
                recurring_charge.recurring_order.last_charge_at = timezone.now()
                recurring_charge.recurring_order.last_error = ""
                recurring_charge.recurring_order.save(
                    update_fields=["last_charge_at", "last_error", "updated_at"]
                )

            result["updated"] = bool(payment_fields) or bool(order_fields)
            result["reason"] = "succeeded"

        elif verified_status == "canceled":
            payment_changed = payment.status != Payment.STATUS_CANCELLED
            if payment_changed:
                payment.status = Payment.STATUS_CANCELLED
                payment.save(update_fields=["status", "updated_at"])
            if (
                order.status == Order.STATUS_NEW
                and order.payment_status == Order.PAYMENT_STATUS_PENDING
            ):
                order.status = Order.STATUS_CANCELLED
                order.save(update_fields=["status"])
                result["order_status_changed"] = True
                notify_status = Order.STATUS_CANCELLED
            from apps.orders.models import RecurringCharge, RecurringOrder

            recurring_plan = RecurringOrder.objects.select_for_update().filter(
                source_order=order,
                status=RecurringOrder.STATUS_PENDING,
            ).first()
            if recurring_plan:
                recurring_plan.status = RecurringOrder.STATUS_PAUSED
                recurring_plan.last_error = "Первый платёж отменён; автоповтор не активирован."
                recurring_plan.save(update_fields=["status", "last_error", "updated_at"])

            recurring_charge = RecurringCharge.objects.select_for_update().filter(order=order).first()
            if recurring_charge:
                recurring_charge.status = RecurringCharge.STATUS_FAILED
                recurring_charge.error_message = "ЮKassa отменила автоплатёж."
                recurring_charge.save(update_fields=["status", "error_message", "updated_at"])
                recurring_charge.recurring_order.status = RecurringOrder.STATUS_PAUSED
                recurring_charge.recurring_order.last_error = recurring_charge.error_message
                recurring_charge.recurring_order.save(
                    update_fields=["status", "last_error", "updated_at"]
                )
            result["updated"] = payment_changed or result["order_status_changed"]
            result["reason"] = "canceled"
        else:
            result["reason"] = verified_status or "unknown_status"

    if notify_status:
        from apps.orders.tasks import send_order_status_email

        try:
            send_order_status_email.delay(result["order_id"], notify_status)
        except Exception:
            logger.exception("Could not queue order status notification")

    if create_waybill:
        from apps.orders.tasks import create_cdek_waybill

        try:
            create_cdek_waybill.delay(result["order_id"])
        except Exception:
            logger.exception("Could not queue CDEK waybill creation")

    return result


def sync_payment_from_yookassa(payment):
    """Fetch and apply the current status for a local Payment instance."""
    verified = fetch_yookassa_payment(payment.yookassa_id)
    values = verified_payment_values(verified)
    return apply_verified_payment(
        values["payment_id"],
        values["status"],
        values["order_id"] or payment.order_id,
        values["amount"],
        values["saved_payment_method_id"],
        values["payment_method_saved"],
        values["payment_method_type"],
        values["card_last4"],
    )
