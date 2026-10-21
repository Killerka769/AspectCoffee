from email.utils import parseaddr

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

from apps.catalog.models import SiteSettings


class ContactDeliveryError(RuntimeError):
    pass


def recipient_address():
    nondelivering = ("console.EmailBackend", "dummy.EmailBackend", "locmem.EmailBackend", "filebased.EmailBackend")
    if not settings.DEBUG and settings.EMAIL_BACKEND.endswith(nondelivering):
        raise ContactDeliveryError("Production needs a delivering email backend")
    site = SiteSettings.objects.filter(pk=1).first()
    value = (site.contact_email if site else "") or getattr(settings, "CONTACT_EMAIL", "") or settings.DEFAULT_FROM_EMAIL
    address = parseaddr(value)[1]
    try:
        validate_email(address)
    except ValidationError:
        raise ContactDeliveryError("Configure the site's contact email") from None
    return address
