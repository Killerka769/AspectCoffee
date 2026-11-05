from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from allauth.socialaccount.models import SocialApp
from django.contrib.sites.models import Site

from apps.catalog.models import Product, ProductVariant
from apps.orders.models import Cart, CartItem, PromoCode
from apps.users.models import User


class CartHeaderRegressionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="cart-header@example.com",
            password="Strongpass1",
        )
        self.product = Product.objects.create(name="Тестовый кофе", slug="test-coffee")
        self.variant = ProductVariant.objects.create(
            product=self.product,
            weight=250,
            price=Decimal("626.67"),
            stock_qty=10,
        )
        now = timezone.now()
        self.promo = PromoCode.objects.create(
            code="FRST15",
            discount_type=PromoCode.DISCOUNT_PERCENT,
            discount_value=Decimal("15"),
            valid_from=now - timedelta(days=1),
            valid_to=now + timedelta(days=30),
        )
        self.cart = Cart.objects.create(user=self.user, promo_code=self.promo)
        self.client.force_login(self.user)

    def test_header_context_uses_subtotal_while_cart_total_keeps_discount(self):
        CartItem.objects.create(cart=self.cart, variant=self.variant, qty=1)

        response = self.client.get(reverse("catalog:index"))

        self.assertEqual(response.context["cart_total"], Decimal("626.67"))
        self.assertEqual(response.context["cart_promo_code"], "FRST15")
        self.assertEqual(self.cart.total, Decimal("532.67"))
        self.assertContains(response, "window.__CART_TOTAL_PRICE__ = 627;")
        self.assertNotContains(response, 'id="mob-nav-cart-badge"')
        self.assertNotContains(response, 'id="mob-bottom-nav"')

    def test_cart_api_returns_subtotal_separately_from_discounted_total(self):
        response = self.client.post(
            reverse("orders:add_to_cart"),
            {"variant_id": self.variant.pk, "qty": 1},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["subtotal"], "626.67")
        self.assertEqual(response.json()["total"], "532.67")

    def test_applied_home_promo_is_disabled_and_labelled(self):
        response = self.client.get(reverse("catalog:index"))

        self.assertEqual(response.context["cart_promo_code"], "FRST15")
        self.assertEqual(self.cart.promo_code_id, self.promo.pk)

    def test_basket_heading_uses_product_plural_forms(self):
        CartItem.objects.create(cart=self.cart, variant=self.variant, qty=1)
        site = Site.objects.get_current()
        for provider in ("yandex", "vk"):
            app = SocialApp.objects.create(
                provider=provider,
                name=provider,
                client_id=f"{provider}-cart-test-client",
                secret="test-secret",
            )
            app.sites.add(site)

        response = self.client.get(reverse("orders:basket"))

        self.assertContains(response, 'id="korzina-count">1</span>')
        self.assertContains(response, 'id="korzina-count-word">товар</span>')
        self.assertContains(response, "function tcProductWord(value)")
        self.assertNotContains(response, "function tcSortWord(value)")

    def test_mini_cart_explains_promo_discount(self):
        CartItem.objects.create(cart=self.cart, variant=self.variant, qty=1)

        response = self.client.get(reverse("orders:mini_cart"))

        self.assertContains(response, "Товары")
        self.assertContains(response, "Промокод FRST15")
        self.assertContains(response, "−94 ₽")
        self.assertContains(response, "533 ₽")
