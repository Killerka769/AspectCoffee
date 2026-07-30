from django.conf import settings
from django.db import DatabaseError


def recurring_payments_enabled():
    """Return the effective recurring-payment switch controlled by admin.

    The environment switch is the emergency infrastructure guard.  When it is
    enabled, the administrator can still turn the feature on or off without a
    deployment through the singleton site settings record.
    """

    if not getattr(settings, "YOOKASSA_RECURRENT_ENABLED", False):
        return False

    try:
        from apps.catalog.models import SiteSettings

        value = (
            SiteSettings.objects.filter(pk=1)
            .values_list("recurring_payments_enabled", flat=True)
            .first()
        )
    except DatabaseError:
        # Keep startup, migrations and recovery commands operational when the
        # database or the new column is temporarily unavailable.
        return False

    return True if value is None else bool(value)
