"""Report effective integration configuration without sending requests or secrets."""
import json

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from apps.delivery.cdek import CDEKClient


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument("--require-configured", action="store_true")

    def handle(self, *args, **options):
        try:
            client = CDEKClient()
        except Exception as error:
            raise CommandError("Invalid CDEK endpoint/mode configuration: " + type(error).__name__) from None
        yookassa_ready = bool(settings.YOOKASSA_SHOP_ID and settings.YOOKASSA_SECRET_KEY)
        smtp_ready = settings.EMAIL_BACKEND == "django.core.mail.backends.smtp.EmailBackend" and bool(settings.EMAIL_HOST)
        result = {
            "yookassa": {"configured": yookassa_ready, "credentials_source": "Django settings / server environment", "external_verified": False},
            "cdek": {"configured": client.configured(), "test_mode": settings.CDEK_TEST_MODE, "endpoint": client.base_url, "external_verified": False},
            "email": {"backend": settings.EMAIL_BACKEND, "smtp_configured": smtp_ready, "external_verified": False},
            "network_requests_sent": 0,
        }
        self.stdout.write(json.dumps(result, indent=2))
        if options["require_configured"] and not (yookassa_ready and client.configured() and smtp_ready):
            raise CommandError("Configure payment, delivery and SMTP settings before external acceptance")
