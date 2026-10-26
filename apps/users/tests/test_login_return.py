from unittest.mock import patch

from django.test import TestCase
from django.conf import settings
from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp

from apps.users.models import User


class LoginReturnTests(TestCase):
    def setUp(self):
        site, _ = Site.objects.get_or_create(pk=settings.SITE_ID, defaults={"domain": "testserver", "name": "Test"})
        for provider in ("yandex", "vk"):
            app = SocialApp.objects.create(provider=provider, name=provider, client_id="test-client", secret="test-secret")
            app.sites.add(site)
        self.user = User.objects.create_user(
            email="community-member@example.com",
            password="test-password-123",
        )

    def test_community_destination_is_preserved_by_form_and_oauth_links(self):
        response = self.client.get("/login/?next=/community/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="next" value="/community/"')
        self.assertContains(
            response, 'href="/accounts/yandex/login/?next=/community/"'
        )
        self.assertContains(
            response, 'href="/accounts/vk/login/?next=/community/"'
        )

    @patch("apps.users.verification.is_email_confirmation_enabled", return_value=False)
    def test_password_login_returns_to_community(self, _confirmation_enabled):
        response = self.client.post(
            "/login/",
            {
                "email": self.user.email,
                "password": "test-password-123",
                "next": "/community/",
            },
        )

        self.assertRedirects(response, "/community/", fetch_redirect_response=False)

    @patch("apps.users.verification.is_email_confirmation_enabled", return_value=False)
    def test_external_destination_is_rejected(self, _confirmation_enabled):
        response = self.client.post(
            "/login/",
            {
                "email": self.user.email,
                "password": "test-password-123",
                "next": "https://example.org/",
            },
        )

        self.assertRedirects(response, "/", fetch_redirect_response=False)
