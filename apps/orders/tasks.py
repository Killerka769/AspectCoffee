
from celery import shared_task
from decouple import config
import logging
logger = logging.getLogger(__name__)
@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_order_confirmation(self, order_id: int, awaiting_payment=None):
    from apps.orders.models import Order
    from apps.users.notifications import send_logged_email
    try:
        order = Order.objects.select_related("user").get(pk=order_id)
        online_payment_pending = (
            order.payment_method in (Order.PAYMENT_CARD, Order.PAYMENT_SBP)
            and order.payment_status != Order.PAYMENT_STATUS_PAID
            if awaiting_payment is None
            else bool(awaiting_payment)
        )
        # The checkout task is queued before redirecting to YooKassa. If the
        # webhook wins the race, the dedicated "paid" notification is already
        # authoritative and a late "awaiting payment" email would be misleading.
        if online_payment_pending and order.payment_status == Order.PAYMENT_STATUS_PAID:
            logger.info(
                "Подтверждение ожидания оплаты для заказа #%s пропущено: заказ уже оплачен",
                order.pk,
            )
            return
        if online_payment_pending:
            subject = f"Заказ #{order.pk} ожидает оплаты"
            body = (
                f"Ваш заказ #{order.pk} создан и ожидает оплаты. "
                "Мы примем его в обработку после подтверждения оплаты ЮKassa."
            )
        else:
            subject = f"Заказ #{order.pk} принят"
            body = (
                f"Ваш заказ #{order.pk} успешно оформлен. "
                f"Мы свяжемся с вами по телефону {order.contact_phone}."
            )
        log = send_logged_email(
            recipient=order.contact_email,
            subject=subject,
            body=body,
        )
        if not log.success:
            raise RuntimeError(log.error_message or "SMTP did not accept the message")
        logger.info(f"Подтверждение заказа #{order.pk} отправлено на {order.contact_email}")
    except Exception as exc:
        logger.error(f"Ошибка отправки подтверждения заказа #{order_id}: {exc}")
        raise self.retry(exc=exc)

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_admin_order_notification(self, order_id: int):
    from apps.orders.models import Order
    from apps.users.notifications import send_logged_email
    try:
        order = Order.objects.get(pk=order_id)
        admin_emails = [e for e in [config("ADMIN_EMAIL", default="")] if e]
        if not admin_emails:
            from django.conf import settings
            admin_emails = [settings.DEFAULT_FROM_EMAIL]
        items_text = "\n".join(
            f"  - {item.product_name} ({item.variant_description}) × {item.qty} = {item.price_at_order * item.qty} ₽"
            for item in order.items.all()
        )
        subject = f"Новый заказ #{order.pk}"
        body = (
                f"Новый заказ #{order.pk}\n\n"
                f"Покупатель: {order.contact_name}\n"
                f"Телефон: {order.contact_phone}\n"
                f"Email: {order.contact_email}\n\n"
                f"Получатель: {order.delivery_recipient_name}\n"
                f"Телефон получателя: {order.delivery_recipient_phone}\n\n"
                f"Способ доставки: {order.get_delivery_type_display()}\n"
                f"Способ оплаты: {order.get_payment_method_display()}\n\n"
                f"Товары:\n{items_text}\n\n"
                f"Итого: {order.total_amount} ₽"
        )
        failed = []
        for recipient in admin_emails:
            log = send_logged_email(recipient=recipient, subject=subject, body=body)
            if not log.success:
                failed.append(log.error_message or recipient)
        if failed:
            raise RuntimeError("; ".join(failed))
        logger.info(f"Уведомление админу о заказе #{order.pk} отправлено")
    except Exception as exc:
        logger.error(f"Ошибка отправки уведомления админу о заказе #{order_id}: {exc}")
        raise self.retry(exc=exc)
@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_order_status_email(self, order_id: int, new_status: str):
    from apps.orders.models import Order
    STATUS_MESSAGES = {
        Order.STATUS_PAID: "Ваш заказ оплачен и принят в обработку.",
        Order.STATUS_ASSEMBLING: "Ваш заказ собирается на складе.",
        Order.STATUS_SHIPPED: "Ваш заказ передан в службу доставки.",
        Order.STATUS_DELIVERED: "Ваш заказ доставлен.",
        Order.STATUS_COMPLETED: "Заказ успешно завершён. Спасибо за покупку!",
        Order.STATUS_CANCELLED: "Ваш заказ отменён.",
    }
    from apps.users.notifications import send_logged_email
    try:
        order = Order.objects.get(pk=order_id)
        message = STATUS_MESSAGES.get(new_status, f"Статус заказа изменён на: {new_status}")
        subject = f"Заказ #{order.pk}: {order.get_status_display()}"
        track_info = f"\nТрек-номер СДЭК для отслеживания: {order.cdek_track_number}" if order.cdek_track_number else ""
        body = (
            f"Здравствуйте, {order.contact_name}!\n\n{message}\n\n"
            f"Заказ #{order.pk} на сумму {order.total_amount} ₽."
            f"{track_info}\n\nС уважением, Aspect Coffee."
        )
        log = send_logged_email(
            recipient=order.contact_email,
            subject=subject,
            body=body,
        )
        if not log.success:
            raise RuntimeError(log.error_message or "SMTP did not accept the message")
        if new_status in (Order.STATUS_DELIVERED, Order.STATUS_COMPLETED) and order.user:
            points = int(order.total_amount // 100)
            if points > 0:
                order.user.earn_bonus(points, order=order)
        if new_status == Order.STATUS_CANCELLED and order.user:
            from apps.users.models import BonusTransaction
            BonusTransaction.objects.filter(
                user=order.user, order=order, type=BonusTransaction.TYPE_EARN,
            ).delete()
            order.user.bonus_points = order.user.get_available_bonus_points()
            order.user.save(update_fields=["bonus_points"])
        logger.info(f"Уведомление о статусе заказа #{order_id} отправлено ({new_status})")
    except Exception as exc:
        logger.error(f"Ошибка уведомления о статусе заказа #{order_id}: {exc}")
        raise self.retry(exc=exc)
@shared_task(bind=True, max_retries=3)
def create_cdek_waybill(self, order_id: int):
    from apps.orders.models import Order
    from apps.delivery.cdek import CDEKClient
    from django.db import transaction

    try:
        # Keep the row locked until CDEK answers. If Celery delivers the same
        # task twice, the second worker will see the UUID saved by the first
        # worker and will not create another external order.
        with transaction.atomic():
            order = Order.objects.select_for_update().get(pk=order_id)
            if order.delivery_type not in (
                Order.DELIVERY_CDEK_PVZ,
                Order.DELIVERY_CDEK_DOOR,
            ):
                return
            if order.cdek_order_uuid:
                logger.info(
                    "Накладная СДЭК для заказа #%s уже существует: %s",
                    order_id,
                    order.cdek_order_uuid,
                )
                return str(order.cdek_order_uuid)

            client = CDEKClient()
            waybill = client.create_order(order)
            if waybill.get("error"):
                raise RuntimeError(waybill["error"])
            waybill_uuid = waybill.get("entity", {}).get("uuid")
            if not waybill_uuid:
                raise RuntimeError("СДЭК не вернул UUID созданной накладной")
            order.cdek_order_uuid = waybill_uuid
            order.save(update_fields=["cdek_order_uuid"])
        logger.info(f"Накладная СДЭК для заказа #{order_id} создана: {order.cdek_order_uuid}")
        return str(order.cdek_order_uuid)
    except Order.DoesNotExist:
        logger.warning("Заказ #%s для создания накладной СДЭК не найден", order_id)
        return None
    except Exception as exc:
        logger.error(f"Ошибка создания накладной СДЭК для заказа #{order_id}: {exc}")
        raise self.retry(exc=exc)
@shared_task
def check_cdek_tracking(order_id: int = None):
    from apps.orders.models import Order
    from apps.delivery.cdek import CDEKClient
    orders = Order.objects.filter(cdek_order_uuid__isnull=False)
    if order_id:
        orders = orders.filter(pk=order_id)
    for order in orders:
        try:
            client = CDEKClient()
            info = client.get_order(str(order.cdek_order_uuid))
            track = info.get("entity", {}).get("cdek_number", "")
            if track and not order.cdek_track_number:
                order.cdek_track_number = track
                order.save(update_fields=["cdek_track_number"])
                logger.info(f"Трек-номер СДЭК для заказа #{order.pk} получен: {track}")
        except Exception as exc:
            logger.error(f"Ошибка получения трек-номера СДЭК для заказа #{order.pk}: {exc}")
@shared_task
def update_product_ratings():
    from django.db.models import Avg, Count
    from apps.catalog.models import Product, Review
    for product in Product.objects.all():
        agg = product.reviews.filter(is_approved=True).aggregate(
            avg=Avg("rating"), count=Count("id"),
        )
        Product.objects.filter(pk=product.pk).update(
            rating_avg=round(agg["avg"], 2) if agg["avg"] is not None else 0,
            reviews_count=agg["count"] or 0,
        )
