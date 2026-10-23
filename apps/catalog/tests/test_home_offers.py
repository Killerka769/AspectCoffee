from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.catalog.views import _available_home_promo, _home_loyalty_offer
from apps.orders.models import Order, PromoCode
from apps.users.models import User


class HomeOfferTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="offers@example.com", password="test-pass-123")
        now = timezone.now()
        self.first_promo = PromoCode.objects.create(
            code="FIRST15",
            discount_type=PromoCode.DISCOUNT_PERCENT,
            discount_value=Decimal("15"),
            valid_from=now - timedelta(days=1),
            valid_to=now + timedelta(days=30),
        )
        self.second_promo = PromoCode.objects.create(
            code="SECOND10",
            discount_type=PromoCode.DISCOUNT_PERCENT,
            discount_value=Decimal("10"),
            valid_from=now - timedelta(days=1),
            valid_to=now + timedelta(days=30),
        )

    def create_order(self, **overrides):
        values = {
            "user": self.user,
            "delivery_type": Order.DELIVERY_PICKUP,
            "delivery_address": {},
            "payment_method": Order.PAYMENT_CARD,
            "payment_status": Order.PAYMENT_STATUS_PAID,
            "status": Order.STATUS_PAID,
            "total_amount": Decimal("6000"),
        }
        values.update(overrides)
        return Order.objects.create(**values)

    def test_first_unused_promo_is_selected(self):
        self.assertEqual(_available_home_promo(self.user), self.first_promo)

    def test_second_promo_is_selected_after_first_was_used(self):
        self.create_order(promo_code=self.first_promo)
        self.assertEqual(_available_home_promo(self.user), self.second_promo)

    def test_earned_discount_is_returned_with_available_promo(self):
        self.user.wholesale_discount = 3
        self.user.save(update_fields=["wholesale_discount"])
        self.create_order(promo_code=self.first_promo)

        offer = _home_loyalty_offer(self.user)

        self.assertEqual(_available_home_promo(self.user), self.second_promo)
        self.assertEqual(offer["discount_percent"], 3)
        self.assertEqual(offer["total_spent"], Decimal("6000"))

    def test_unpaid_new_order_does_not_earn_discount(self):
        self.create_order(
            payment_status=Order.PAYMENT_STATUS_PENDING,
            status=Order.STATUS_NEW,
        )

        offer = _home_loyalty_offer(self.user)

        self.assertEqual(offer["discount_percent"], 0)
        self.assertEqual(offer["total_spent"], 0)
