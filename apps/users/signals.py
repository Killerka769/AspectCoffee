from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import EmailLog, User
from .notifications import create_notification, email_log_kind


@receiver(post_save, sender=EmailLog)
def email_log_to_user_notification(sender, instance, created, **kwargs):
    if not created or hasattr(instance, "user_notification"):
        return
    user = User.objects.filter(email__iexact=instance.recipient, is_active=True).first()
    if not user:
        return
    create_notification(
        user=user,
        title=instance.subject,
        body=instance.body or "",
        kind=email_log_kind(instance.subject),
        email_log=instance,
    )
