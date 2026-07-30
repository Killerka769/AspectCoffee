
import logging
from celery import shared_task
from django.db import transaction

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def check_payment_timeout(self, payment_id: int):
    """
    Cancel order if payment is still pending after 30 minutes.
    Fix #3v3: always check payment status before cancelling —
    prevents cancelling an already-paid order if webhook was delayed.
    """
    from apps.payments.models import Payment
    from apps.orders.models import Order

    try:
        payment = Payment.objects.select_related("order").get(id=payment_id)

        if payment.status == Payment.STATUS_SUCCEEDED:
            logger.info(f"Payment #{payment_id}: already succeeded, timeout task skipped")
            return

        if payment.order and payment.order.payment_status == Order.PAYMENT_STATUS_PAID:
            logger.info(f"Payment #{payment_id}: order already paid, timeout task skipped")
            return

        # The webhook may be delayed or misconfigured. YooKassa's API is the
        # source of truth, so reconcile before cancelling a local order.
        from apps.payments.services import sync_payment_from_yookassa
        sync_result = sync_payment_from_yookassa(payment)
        payment.refresh_from_db()
        if payment.status == Payment.STATUS_SUCCEEDED:
            logger.info(
                "Payment #%s succeeded in YooKassa; timeout cancellation skipped",
                payment_id,
            )
            return sync_result

        with transaction.atomic():
            payment.status = Payment.STATUS_CANCELLED
            payment.save(update_fields=["status", "updated_at"])

            if payment.order:
                order = payment.order
                order.status = Order.STATUS_CANCELLED
                order.save(update_fields=["status"])
                logger.info(f"Order #{order.id} cancelled due to payment timeout")

                from apps.orders.tasks import send_order_status_email
                try:
                    send_order_status_email.delay(order.id, Order.STATUS_CANCELLED)
                except Exception as e:
                    logger.error(f"Failed to queue cancellation email: {e}")

    except Payment.DoesNotExist:
        logger.warning(f"check_payment_timeout: Payment #{payment_id} not found")
    except Exception as exc:
        logger.error(f"check_payment_timeout error for payment #{payment_id}: {exc}")
        raise self.retry(exc=exc)


@shared_task
def sync_pending_payments():
    """Reconcile recent pending payments if a YooKassa webhook was missed."""
    from datetime import timedelta

    from django.utils import timezone

    from apps.payments.models import Payment
    from apps.payments.services import sync_payment_from_yookassa

    cutoff = timezone.now() - timedelta(days=30)
    payments = Payment.objects.filter(
        status=Payment.STATUS_PENDING,
        created_at__gte=cutoff,
    ).order_by("created_at")[:200]
    result = {"checked": 0, "updated": 0, "errors": 0}
    for payment in payments:
        result["checked"] += 1
        try:
            synced = sync_payment_from_yookassa(payment)
            if synced.get("updated"):
                result["updated"] += 1
        except Exception:
            result["errors"] += 1
            logger.exception("Failed to reconcile YooKassa payment #%s", payment.pk)
    return result


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_refund(self, order_id: int):
    """
    Initiate YooKassa refund for a paid order.
    Fix #5v3: cancel_order with paid status triggers this task.
    """
    from apps.payments.models import Payment
    from apps.orders.models import Order
    from django.conf import settings

    try:
        order = Order.objects.select_related("payment").get(id=order_id)

        if not hasattr(order, "payment"):
            logger.warning(f"process_refund: No payment found for order #{order_id}")
            return

        payment = order.payment
        if payment.status != Payment.STATUS_SUCCEEDED:
            logger.warning(f"process_refund: Payment for order #{order_id} is not succeeded (status={payment.status})")
            return

        shop_id = getattr(settings, "YOOKASSA_SHOP_ID", "")
        secret_key = getattr(settings, "YOOKASSA_SECRET_KEY", "")
        if not shop_id or not secret_key:
            logger.error("process_refund: YooKassa not configured")
            return

        import yookassa
        import uuid
        yookassa.Configuration.account_id = shop_id
        yookassa.Configuration.secret_key = secret_key

        refund = yookassa.Refund.create({
            "amount": {
                "value": str(payment.amount),
                "currency": "RUB",
            },
            "payment_id": payment.yookassa_id,
        }, str(uuid.uuid4()))

        with transaction.atomic():
            payment.status = Payment.STATUS_REFUNDED
            payment.yookassa_refund_id = refund.id
            payment.save(update_fields=["status", "yookassa_refund_id", "updated_at"])

            order.payment_status = Order.PAYMENT_STATUS_REFUNDED
            order.save(update_fields=["payment_status"])

        logger.info(f"Refund created for order #{order_id}: refund_id={refund.id}")

        from apps.orders.tasks import send_order_status_email
        try:
            send_order_status_email.delay(order.id, "refunded")
        except Exception as e:
            logger.error(f"Failed to queue refund email: {e}")

    except Exception as exc:
        logger.error(f"process_refund error for order #{order_id}: {exc}")
        raise self.retry(exc=exc)


def _create_order_for_recurring_charge(charge):
    """Create one immutable order snapshot for a scheduled recurring charge."""
    from apps.orders.models import Order, OrderItem

    source = charge.recurring_order.source_order
    source_items = list(source.items.select_related("variant__product"))
    if not source_items:
        raise ValueError("В исходном заказе нет товаров")

    unavailable = []
    for item in source_items:
        variant = item.variant
        if not variant or not variant.product.is_active:
            unavailable.append(item.product_name)
            continue
        if not variant.is_preorder and variant.stock_qty < item.qty:
            unavailable.append(item.product_name)
    if unavailable:
        raise ValueError("Недостаточный остаток: " + ", ".join(unavailable))

    order = Order.objects.create(
        user=source.user,
        status=Order.STATUS_NEW,
        delivery_type=source.delivery_type,
        delivery_address=source.delivery_address,
        delivery_cost=source.delivery_cost,
        cdek_pvz_code=source.cdek_pvz_code,
        cdek_pvz_address=source.cdek_pvz_address,
        payment_method=Order.PAYMENT_CARD,
        payment_status=Order.PAYMENT_STATUS_PENDING,
        promo_code=None,
        discount_amount=source.discount_amount,
        total_amount=source.total_amount,
        contact_name=source.contact_name,
        contact_phone=source.contact_phone,
        contact_email=source.contact_email,
        comment=source.comment,
        is_organization=source.is_organization,
        org_name=source.org_name,
        org_inn=source.org_inn,
        recipient_name=source.recipient_name,
        recipient_phone=source.recipient_phone,
        phone_code=source.phone_code,
    )
    OrderItem.objects.bulk_create([
        OrderItem(
            order=order,
            variant=item.variant,
            product_name=item.product_name,
            variant_description=item.variant_description,
            qty=item.qty,
            price_at_order=item.price_at_order,
        )
        for item in source_items
    ])
    charge.order = order
    charge.save(update_fields=["order", "updated_at"])
    return order


@shared_task(bind=True, max_retries=2, default_retry_delay=300)
def process_recurring_charge(self, charge_id: int):
    """Charge a saved YooKassa method once for a prepared schedule slot."""
    from django.conf import settings
    from django.utils import timezone

    from apps.orders.models import RecurringCharge, RecurringOrder
    from apps.payments.models import Payment

    from apps.orders.recurring import recurring_payments_enabled

    if not recurring_payments_enabled():
        return {"status": "disabled"}

    try:
        with transaction.atomic():
            charge = (
                RecurringCharge.objects.select_for_update()
                .select_related("recurring_order__source_order", "recurring_order__user")
                .get(pk=charge_id)
            )
            plan = charge.recurring_order
            if charge.status == RecurringCharge.STATUS_SUCCEEDED:
                return {"status": "already_succeeded"}
            if plan.status != RecurringOrder.STATUS_ACTIVE or not plan.saved_payment_method_id:
                return {"status": "inactive"}
            charge.status = RecurringCharge.STATUS_PROCESSING
            charge.error_message = ""
            charge.save(update_fields=["status", "error_message", "updated_at"])
            order = charge.order or _create_order_for_recurring_charge(charge)

        import yookassa

        yookassa.Configuration.account_id = settings.YOOKASSA_SHOP_ID
        yookassa.Configuration.secret_key = settings.YOOKASSA_SECRET_KEY
        payment_data = yookassa.Payment.create({
            "amount": {"value": str(order.total_amount), "currency": "RUB"},
            "payment_method_id": plan.saved_payment_method_id,
            "capture": True,
            "description": f"Автоповтор заказа #{plan.source_order_id} — Aspect Coffee",
            "metadata": {
                "order_id": str(order.id),
                "recurring_order_id": str(plan.id),
                "recurring_charge_id": str(charge.id),
            },
        }, str(charge.idempotency_key))

        Payment.objects.update_or_create(
            order=order,
            defaults={
                "yookassa_id": payment_data.id,
                "amount": order.total_amount,
                "status": Payment.STATUS_PENDING,
                "confirmation_url": "",
            },
        )
        order.payment_id = payment_data.id
        order.save(update_fields=["payment_id"])

        from apps.payments.services import apply_verified_payment, verified_payment_values

        values = verified_payment_values(payment_data)
        apply_verified_payment(
            values["payment_id"], values["status"], values["order_id"] or order.id,
            values["amount"], values["saved_payment_method_id"],
            values["payment_method_saved"], values["payment_method_type"],
            values["card_last4"],
        )
        return {"status": values["status"], "order_id": order.id}
    except Exception as exc:
        logger.exception("Recurring charge #%s failed", charge_id)
        with transaction.atomic():
            charge = RecurringCharge.objects.select_for_update().select_related("recurring_order").filter(pk=charge_id).first()
            if charge:
                charge.status = RecurringCharge.STATUS_FAILED
                charge.error_message = str(exc)[:2000]
                charge.save(update_fields=["status", "error_message", "updated_at"])
                plan = charge.recurring_order
                plan.status = RecurringOrder.STATUS_PAUSED
                plan.last_error = str(exc)[:2000]
                plan.save(update_fields=["status", "last_error", "updated_at"])
        raise self.retry(exc=exc)


@shared_task
def process_due_recurring_orders():
    """Create one idempotent charge slot for every plan due now."""
    from datetime import timedelta

    from django.conf import settings
    from django.utils import timezone

    from apps.orders.models import RecurringCharge, RecurringOrder

    from apps.orders.recurring import recurring_payments_enabled

    if not recurring_payments_enabled():
        return {"status": "disabled", "queued": 0}

    now = timezone.now()
    due_ids = list(
        RecurringOrder.objects.filter(
            status=RecurringOrder.STATUS_ACTIVE,
            next_charge_at__isnull=False,
            next_charge_at__lte=now,
        ).values_list("pk", flat=True)[:50]
    )
    queued = 0
    for plan_id in due_ids:
        with transaction.atomic():
            plan = RecurringOrder.objects.select_for_update().get(pk=plan_id)
            if plan.status != RecurringOrder.STATUS_ACTIVE or not plan.next_charge_at or plan.next_charge_at > now:
                continue
            scheduled_for = plan.next_charge_at
            charge, created = RecurringCharge.objects.get_or_create(
                recurring_order=plan,
                scheduled_for=scheduled_for,
            )
            plan.next_charge_at = max(scheduled_for, now) + timedelta(weeks=plan.interval_weeks)
            plan.save(update_fields=["next_charge_at", "updated_at"])
        if created or charge.status in (RecurringCharge.STATUS_PENDING, RecurringCharge.STATUS_FAILED):
            process_recurring_charge.delay(charge.id)
            queued += 1
    return {"status": "ok", "queued": queued}
