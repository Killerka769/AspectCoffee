
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender="warehouse.StockItem")
def check_low_stock(sender, instance, **kwargs):
    """
    Trigger low-stock alert when qty drops below min_qty.

    Fix #3v3 — spam prevention:
    1. Skip newly created items (initial stock entry).
    2. Only trigger if 'qty' field was actually updated (update_fields check).
    3. Task itself re-checks qty in case replenishment happened before it ran.
    """
    if kwargs.get("created"):
        return

    update_fields = kwargs.get("update_fields") or []
    if update_fields and "qty" not in update_fields:
        return

    if instance.qty < instance.min_qty:
        from apps.warehouse.tasks import send_low_stock_alert
        send_low_stock_alert.delay(instance.id)
        logger.info(f"Low-stock alert queued for StockItem #{instance.id} (qty={instance.qty}, min={instance.min_qty})")
