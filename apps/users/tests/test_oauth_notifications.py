from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from django.contrib.sessions.middleware import SessionMiddleware
from django.conf import settings
from django.core import mail
from django.test import RequestFactory, TestCase, override_settings
from django.urls import resolve
from allauth.socialaccount.providers.yandex.provider import YandexProvider

from apps.users.models import EmailLog, PushSubscription, User, UserNotification
from apps.users.notifications import send_logged_email
from apps.users.oauth_views import (
    RussianYandexOAuth2Adapter,
    vkid_login,
    yandex_oauth_login,
)


class OAuthRegressionTests(TestCase):
    def test_vk_route_uses_current_vkid_pkce_endpoint_in_russian(self):
        request = RequestFactory().get("/accounts/vk/login/?next=/basket/")
        SessionMiddleware(lambda req: None).process_request(request)
        request.session.save()
        provider = SimpleNamespace(app=SimpleNamespace(client_id="54657505"))
        adapter = SimpleNamespace(get_provider=lambda *args, **kwargs: provider)

        with patch("apps.users.oauth_views.get_adapter", return_value=adapter):
            response = vkid_login(request)

        location = urlparse(response["Location"])
        params = parse_qs(location.query)
        self.assertEqual((location.scheme, location.netloc, location.path), ("https", "id.vk.ru", "/authorize"))
        self.assertEqual(params["lang_id"], ["0"])
        self.assertEqual(params["code_challenge_method"], ["s256"])
        self.assertEqual(params["client_id"], ["54657505"])
        self.assertEqual(params["scope"], ["phone email"])
        self.assertIn("stats_info", params)
        self.assertEqual(params["v"], ["2.6.6"])
        self.assertTrue(params["code_challenge"][0])
        self.assertTrue(request.session["vkid_code_verifier"])
        self.assertEqual(request.session["vkid_next"], "/basket/")

    def test_project_routes_override_legacy_vk_provider(self):
        self.assertIs(resolve("/accounts/vk/login/").func, vkid_login)

    def test_yandex_authorization_uses_russian_host(self):
        self.assertEqual(
            RussianYandexOAuth2Adapter.authorize_url,
            "https://oauth.yandex.ru/authorize",
        )
        self.assertIs(resolve("/accounts/yandex/login/").func, yandex_oauth_login)

        request = RequestFactory().get("/accounts/yandex/login/?next=/basket/")
        provider = SimpleNamespace(
            oauth2_adapter_class=None,
            redirect_from_request=lambda req: SimpleNamespace(status_code=302),
        )
        adapter = SimpleNamespace(get_provider=lambda *args, **kwargs: provider)
        with patch("apps.users.oauth_views.get_adapter", return_value=adapter):
            response = yandex_oauth_login(request)

        self.assertEqual(response.status_code, 302)
        self.assertIs(provider.oauth2_adapter_class, RussianYandexOAuth2Adapter)
        self.assertEqual(
            settings.SOCIALACCOUNT_PROVIDERS["yandex"]["AUTH_PARAMS"],
            {"force_confirm": "yes"},
        )
        configured_provider = YandexProvider(
            request=request,
            app=SimpleNamespace(settings={}),
        )
        self.assertEqual(
            configured_provider.get_auth_params(),
            {"force_confirm": "yes"},
        )


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class NotificationRegressionTests(TestCase):
    def test_logged_email_is_really_sent_and_creates_bell_notification(self):
        user = User.objects.create_user(
            email="notice@example.com",
            password="Strongpass1",
        )

        log = send_logged_email(
            recipient=user.email,
            subject="Заказ #10 принят",
            body="Ваш заказ принят.",
        )

        self.assertTrue(log.success)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [user.email])
        self.assertTrue(
            UserNotification.objects.filter(user=user, email_log=log).exists()
        )
        self.assertEqual(EmailLog.objects.filter(recipient=user.email).count(), 1)

    def test_review_publication_notification_uses_canonical_email_and_bell(self):
        from apps.catalog.models import Product, Review
        from apps.catalog.tasks import send_user_review_published_notification

        user = User.objects.create_user(
            email="review-notice@example.com",
            password="Strongpass1",
        )
        product = Product.objects.create(name="Товар уведомления", slug="notice-product")
        review = Review.objects.create(
            product=product,
            user=user,
            rating=5,
            text="Текст отзыва",
            status=Review.STATUS_PUBLISHED,
        )

        sent = send_user_review_published_notification.run(review.pk)

        self.assertTrue(sent)
        log = EmailLog.objects.get(recipient=user.email)
        self.assertTrue(log.success)
        self.assertTrue(UserNotification.objects.filter(user=user, email_log=log).exists())

    def test_retired_recipe_notification_is_not_exposed(self):
        from apps.catalog import tasks

        self.assertFalse(hasattr(tasks, "send_user_recipe_published_notification"))

    @override_settings(
        WEBPUSH_VAPID_PRIVATE_KEY="test-private-key",
        WEBPUSH_VAPID_SUBJECT="mailto:notice@example.com",
    )
    @patch("pywebpush.webpush")
    def test_web_push_sends_to_active_subscription(self, webpush):
        from apps.users.tasks import send_web_push_notification

        user = User.objects.create_user(
            email="push-notice@example.com",
            password="Strongpass1",
        )
        notification = UserNotification.objects.create(
            user=user,
            title="Проверка push",
            body="Текст уведомления",
            url="/account/notifications/",
        )
        PushSubscription.objects.create(
            user=user,
            endpoint="https://push.example.test/subscription",
            p256dh="test-p256dh",
            auth="test-auth",
        )

        sent = send_web_push_notification.run(notification.pk)

        self.assertEqual(sent, 1)
        webpush.assert_called_once()
