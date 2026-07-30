import json
import logging

from celery import shared_task
from django.conf import settings

from .models import PushSubscription, UserNotification

logger = logging.getLogger(__name__)


@shared_task
def send_web_push_notification(notification_id):
    private_key = getattr(settings, "WEBPUSH_VAPID_PRIVATE_KEY", "")
    subject = getattr(settings, "WEBPUSH_VAPID_SUBJECT", "")
    if not private_key or not subject:
        return 0

    try:
        from pywebpush import WebPushException, webpush
    except ImportError:
        logger.error("pywebpush is not installed; push notification was skipped")
        return 0

    try:
        notification = UserNotification.objects.select_related("user").get(pk=notification_id)
    except UserNotification.DoesNotExist:
        return 0

    payload = json.dumps(
        {
            "title": notification.title,
            "body": notification.body,
            "url": notification.url or "/account/notifications/",
            "tag": f"aspect-notification-{notification.pk}",
            "notification_id": notification.pk,
        },
        ensure_ascii=False,
    )
    sent = 0
    subscriptions = PushSubscription.objects.filter(user=notification.user, is_active=True)
    for subscription in subscriptions.iterator():
        info = {
            "endpoint": subscription.endpoint,
            "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
        }
        try:
            webpush(
                subscription_info=info,
                data=payload,
                vapid_private_key=private_key,
                vapid_claims={"sub": subject},
            )
            sent += 1
        except WebPushException as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if status in (404, 410):
                subscription.is_active = False
                subscription.save(update_fields=["is_active", "updated_at"])
            else:
                logger.warning("Web Push failed for subscription %s: %s", subscription.pk, exc)
        except Exception:
            logger.exception("Unexpected Web Push failure for subscription %s", subscription.pk)
    return sent
