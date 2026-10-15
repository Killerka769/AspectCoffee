from django.conf import settings
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand, CommandError

from allauth.socialaccount.models import SocialApp, SocialToken

from apps.users.models import PushSubscription


class Command(BaseCommand):
    help = "Remove production-only connections from a copied test database."

    def handle(self, *args, **options):
        if getattr(settings, "ENVIRONMENT", "") != "test":
            raise CommandError("This command is allowed only when ENVIRONMENT=test")

        site, _ = Site.objects.update_or_create(
            pk=settings.SITE_ID,
            defaults={
                "domain": "test.aspectcoffee.ru",
                "name": "Aspect Coffee TEST",
            },
        )

        token_count, _ = SocialToken.objects.all().delete()
        app_count, _ = SocialApp.objects.all().delete()
        push_count, _ = PushSubscription.objects.all().delete()

        self.stdout.write(
            self.style.SUCCESS(
                "Test database prepared: "
                f"site={site.domain}, social_tokens={token_count}, "
                f"social_apps={app_count}, push_subscriptions={push_count}"
            )
        )