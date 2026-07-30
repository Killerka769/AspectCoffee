from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction

from .models import EmailLog, UserNotification


def deliver_email(*, recipient, subject, body, html_message=None):
    """Send one email and return a result suitable for an EmailLog row."""
    try:
        sent = send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            html_message=html_message,
            fail_silently=False,
        )
        return bool(sent), ""
    except Exception as exc:
        return False, str(exc)


def send_logged_email(*, recipient, subject, body, html_message=None):
    """Send an email and create the canonical log/bell/push notification."""
    success, error_message = deliver_email(
        recipient=recipient,
        subject=subject,
        body=body,
        html_message=html_message,
    )
    log = EmailLog.objects.create(
        recipient=recipient,
        subject=subject,
        body=body,
        success=success,
        error_message=error_message,
    )
    return log


def create_notification(
    *,
    user,
    title,
    body="",
    url="",
    kind=UserNotification.KIND_INFO,
    actor=None,
    email_log=None,
):
    """Create the canonical bell notification and enqueue its Web Push copy."""
    notification = UserNotification.objects.create(
        user=user,
        actor=actor,
        email_log=email_log,
        title=title[:255],
        body=body,
        url=url[:500],
        kind=kind,
    )

    def enqueue_push():
        try:
            from .tasks import send_web_push_notification

            send_web_push_notification.delay(notification.pk)
        except Exception:
            # The bell notification must never be lost when Redis/Celery is down.
            pass

    transaction.on_commit(enqueue_push)
    return notification


def email_log_kind(subject):
    normalized = (subject or "").lower()
    if "заказ" in normalized or "оплат" in normalized or "достав" in normalized:
        return UserNotification.KIND_ORDER
    return UserNotification.KIND_INFO
