from unittest.mock import patch

from django.core import mail
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from apps.catalog.models import SiteSettings
from apps.pages.models import Inquiry


@override_settings(DEBUG=True, EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class ContactFormTests(TestCase):
    def setUp(self):
        cache.clear()
        site = SiteSettings.load()
        site.contact_email = "inbox@example.com"
        site.save()
        self.data = {"name": "Иван", "email": "visitor@example.net", "message": "Пожалуйста, свяжитесь со мной", "consent": "on", "website": ""}

    def test_all_three_forms_send_to_site_email_with_safe_reply_to(self):
        expected = {
            "contact_us": Inquiry.FormType.CONTACT,
            "partners": Inquiry.FormType.PARTNER,
            "subscription": Inquiry.FormType.SUBSCRIPTION,
            "coffee_in_office": Inquiry.FormType.COFFEE_OFFICE,
        }
        for page, form_type in expected.items():
            with self.subTest(page=page):
                url = reverse("pages:" + page)
                response = self.client.post(url, self.data)
                self.assertRedirects(response, url)
                self.assertEqual(mail.outbox[-1].to, ["inbox@example.com"])
                self.assertEqual(mail.outbox[-1].reply_to, ["visitor@example.net"])
                self.assertIn(self.data["message"], mail.outbox[-1].body)
                self.assertTrue(Inquiry.objects.filter(form_type=form_type, email=self.data["email"], is_processed=False).exists())
        self.assertEqual(len(mail.outbox), 4)
        self.assertEqual(Inquiry.objects.count(), 4)

    def test_validation_and_honeypot_do_not_send_mail(self):
        for changed in ({"email": "invalid"}, {"website": "spam"}, {"consent": ""}, {"message": "x" * 5001}):
            response = self.client.post(reverse("pages:contact_us"), {**self.data, **changed})
            self.assertEqual(response.status_code, 400)
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(Inquiry.objects.count(), 0)

    def test_smtp_failure_is_visible_and_retry_can_succeed(self):
        with patch("django.core.mail.EmailMessage.send", side_effect=OSError("SMTP unavailable")):
            response = self.client.post(reverse("pages:contact_us"), self.data)
        self.assertEqual(response.status_code, 503)
        self.assertContains(response, "Письмо не отправлено", status_code=503)
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(Inquiry.objects.filter(form_type=Inquiry.FormType.CONTACT).count(), 1)
        self.assertEqual(self.client.post(reverse("pages:contact_us"), self.data).status_code, 302)
        self.assertEqual(Inquiry.objects.filter(form_type=Inquiry.FormType.CONTACT).count(), 2)

    def test_zero_mail_result_is_not_success(self):
        with patch("django.core.mail.EmailMessage.send", return_value=0):
            response = self.client.post(reverse("pages:contact_us"), self.data)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(Inquiry.objects.count(), 1)

    def test_repeat_is_throttled_and_redirect_refresh_does_not_resend(self):
        url = reverse("pages:contact_us")
        self.assertEqual(self.client.post(url, self.data).status_code, 302)
        self.client.get(url)
        self.client.get(url)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(self.client.post(url, self.data).status_code, 429)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(Inquiry.objects.count(), 1)

    def test_csrf_protection_is_real(self):
        client = Client(enforce_csrf_checks=True)
        url = reverse("pages:contact_us")
        self.assertEqual(client.post(url, self.data).status_code, 403)
        client.get(url)
        response = client.post(url, {**self.data, "csrfmiddlewaretoken": client.cookies["csrftoken"].value})
        self.assertEqual(response.status_code, 302)

    @override_settings(DEBUG=False)
    def test_nondelivering_production_backend_cannot_show_fake_success(self):
        response = self.client.post(reverse("pages:contact_us"), self.data)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(len(mail.outbox), 0)

    @override_settings(CONTACT_EMAIL="fallback@example.com")
    def test_recipient_fallback_is_explicit(self):
        SiteSettings.objects.update(contact_email="")
        self.client.post(reverse("pages:contact_us"), self.data)
        self.assertEqual(mail.outbox[-1].to, ["fallback@example.com"])
