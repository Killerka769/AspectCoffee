from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.catalog.models import Product, ProductVariant, SiteSettings
from apps.orders.models import Cart, CartItem, Order
from apps.users.models import User


@override_settings(EMAIL_CONFIRMATION_ENABLED=False)
class UserBanTests(TestCase):
    def test_expired_ban_opens_the_account(self):
        user = User.objects.create_user(email="late@example.com", password="Secret123")
        user.is_active = False
        user.ban_reason = "спам"
        user.banned_until = timezone.now() - timedelta(minutes=1)
        user.save()

        self.assertFalse(user.is_banned_now)
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertEqual(user.ban_reason, "")
        self.assertIsNone(user.banned_until)

    def test_active_user_is_not_banned(self):
        user = User.objects.create_user(email="ok@example.com", password="Secret123")
        self.assertFalse(user.is_banned_now)

    def test_login_shows_ban_reason_instead_of_a_wrong_password(self):
        user = User.objects.create_user(email="banned@example.com", password="Secret123")
        user.is_active = False
        user.ban_reason = "спам в отзывах"
        user.banned_until = timezone.now() + timedelta(days=3)
        user.save()

        response = self.client.post("/login/", {
            "email": user.email,
            "password": "Secret123",
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ваш аккаунт заблокирован до")
        self.assertContains(response, "спам в отзывах")
        self.assertNotContains(response, "Неверный email или пароль")
        self.assertFalse(get_user(self.client).is_authenticated)

    def test_wrong_password_stays_a_wrong_password(self):
        user = User.objects.create_user(email="person@example.com", password="Secret123")
        response = self.client.post("/login/", {
            "email": user.email,
            "password": "wrong-pass",
        })
        self.assertContains(response, "Неверный email или пароль")

    def test_normal_login_still_works(self):
        User.objects.create_user(email="person@example.com", password="Secret123")
        response = self.client.post("/login/", {
            "email": "person@example.com",
            "password": "Secret123",
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(get_user(self.client).is_authenticated)

    @override_settings(PAYMENT_COD_ENABLED=False)
    def test_checkout_does_not_log_in_a_banned_account(self):
        SiteSettings.load()
        settings = SiteSettings.objects.get(pk=1)
        settings.enable_pickup = True
        settings.save(update_fields=["enable_pickup"])
        product = Product.objects.create(name="Сорт", slug="sort-ban")
        variant = ProductVariant.objects.create(
            product=product, weight=250, price=Decimal("500.00"), stock_qty=5,
        )
        session = self.client.session
        session.save()
        cart = Cart.objects.create(session_key=session.session_key)
        CartItem.objects.create(cart=cart, variant=variant, qty=1)
        user = User.objects.create_user(email="buyer@example.com", password="Secret123")
        user.is_active = False
        user.ban_reason = "спам"
        user.save()

        with (
            patch("apps.orders.tasks.send_order_confirmation.delay"),
            patch("apps.orders.tasks.send_admin_order_notification.delay"),
        ):
            response = self.client.post("/basket/", {
                "action": "checkout",
                "full_name": "Иван Иванов",
                "phone": "9991112233",
                "phone_code": "+7",
                "email": "buyer@example.com",
                "agree_terms": "on",
                "delivery_type": Order.DELIVERY_PICKUP,
                "payment_method": "card",
                "register_account": "on",
                "reg_password": "Secret123",
                "reg_password2": "Secret123",
            }, HTTP_X_REQUESTED_WITH="XMLHttpRequest")

        self.assertEqual(response.status_code, 400)
        self.assertIn("заблокирован", response.json()["error"])
        self.assertIn("спам", response.json()["error"])
        self.assertFalse(Order.objects.exists())
        self.assertFalse(get_user(self.client).is_authenticated)
        user.refresh_from_db()
        self.assertFalse(user.is_active)
        self.assertEqual(user.phone, "")
