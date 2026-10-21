from django.test import SimpleTestCase, override_settings
from rest_framework.exceptions import ValidationError

from apps.api.serializers import OrderCreateSerializer
from apps.orders.models import Order


class PaymentPolicyTests(SimpleTestCase):
    @override_settings(PAYMENT_COD_ENABLED=False)
    def test_disabled_method_is_rejected_by_api_validation(self):
        with self.assertRaises(ValidationError):
            OrderCreateSerializer().validate_payment_method(Order.PAYMENT_COD)

    @override_settings(PAYMENT_COD_ENABLED=False)
    def test_online_card_method_is_not_disabled(self):
        self.assertEqual(OrderCreateSerializer().validate_payment_method(Order.PAYMENT_CARD), Order.PAYMENT_CARD)
