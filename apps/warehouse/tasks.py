
import logging
from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=120)
def send_low_stock_alert(self, stock_item_id: int):
    """
    Send low-stock email alert to administrators.
    Triggered by StockItem.post_save signal only when qty drops below min_qty.
    """
    from apps.warehouse.models import StockItem
    from apps.users.models import User

    try:
        stock_item = StockItem.objects.select_related("variant__product").get(id=stock_item_id)

        if stock_item.qty >= stock_item.min_qty:
            logger.info(f"Low-stock alert cancelled: stock replenished for {stock_item}")
            return

        # Throttling: only send once per 24 hours for the same item
        now = timezone.now()
        if stock_item.last_low_stock_notification and \
           now - stock_item.last_low_stock_notification < timedelta(hours=24):
            logger.info(f"Low-stock alert throttled for {stock_item}")
            return

        admin_emails = list(
            User.objects.filter(is_staff=True, is_active=True)
            .values_list("email", flat=True)
        )

        if not admin_emails:
            logger.warning("No staff users to send low-stock alert to")
            return

        subject = f"[Внимание] Низкий остаток: {stock_item.variant}"
        context = {
            "stock_item": stock_item,
            "variant": stock_item.variant,
            "product": stock_item.variant.product,
        }
        html_content = render_to_string("email/low_stock_alert.html", context)
        text_content = (
            f"Внимание! Остаток товара '{stock_item.variant}' снизился до {stock_item.qty} шт. "
            f"(минимум: {stock_item.min_qty} шт.)"
        )

        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=admin_emails,
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send()

        stock_item.last_low_stock_notification = now
        stock_item.save(update_fields=["last_low_stock_notification"])

        logger.info(f"Low-stock alert sent for {stock_item} to {admin_emails}")


    except StockItem.DoesNotExist:
        logger.warning(f"send_low_stock_alert: StockItem #{stock_item_id} not found")
    except Exception as exc:
        logger.error(f"send_low_stock_alert error for StockItem #{stock_item_id}: {exc}")
        raise self.retry(exc=exc)
