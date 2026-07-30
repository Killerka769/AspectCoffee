from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.catalog.models import Product, ProductVariant
from apps.orders.models import Order, OrderItem, RecurringCharge, RecurringOrder
from apps.payments.tasks import _create_order_for_recurring_charge, process_due_recurring_orders
from apps.users.models import User


class RecurringPaymentTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="recurring@example.com",
            password="Strongpass1",
        )
        self.product = Product.objects.create(
            name="Кофе для автоповтора",
            slug="recurring-coffee",
            is_active=True,
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            weight=250,
            price=Decimal("627.00"),
            stock_qty=10,
        )
        self.source_order = Order.objects.create(
            user=self.user,
            status=Order.STATUS_PAID,
            delivery_type=Order.DELIVERY_PICKUP,
            delivery_address={"city": "Москва"},
            delivery_cost=Decimal("0"),
            payment_method=Order.PAYMENT_CARD,
            payment_status=Order.PAYMENT_STATUS_PAID,
            total_amount=Decimal("627.00"),
            contact_name="Иван",
            contact_phone="+79000000000",
            contact_email=self.user.email,
        )
        OrderItem.objects.create(
            order=self.source_order,
            variant=self.variant,
            product_name=self.product.name,
            variant_description="250 г",
            qty=1,
            price_at_order=Decimal("627.00"),
        )
        self.plan = RecurringOrder.objects.create(
            source_order=self.source_order,
            user=self.user,
            interval_weeks=2,
            saved_payment_method_id="saved-method-1",
            status=RecurringOrder.STATUS_ACTIVE,
            next_charge_at=timezone.now() - timedelta(minutes=1),
        )

    @override_settings(YOOKASSA_RECURRENT_ENABLED=True)
    @patch("apps.payments.tasks.process_recurring_charge.delay")
    def test_due_plan_creates_one_idempotent_charge_slot(self, delay_mock):
        result = process_due_recurring_orders()

        self.plan.refresh_from_db()
        charge = RecurringCharge.objects.get(recurring_order=self.plan)
        self.assertEqual(result["queued"], 1)
        self.assertGreater(self.plan.next_charge_at, timezone.now())
        delay_mock.assert_called_once_with(charge.pk)

        process_due_recurring_orders()
        self.assertEqual(RecurringCharge.objects.filter(recurring_order=self.plan).count(), 1)

    def test_recurring_order_snapshot_is_created_once(self):
        charge = RecurringCharge.objects.create(
            recurring_order=self.plan,
            scheduled_for=self.plan.next_charge_at,
        )

        order = _create_order_for_recurring_charge(charge)

        charge.refresh_from_db()
        self.assertEqual(charge.order, order)
        self.assertEqual(order.total_amount, self.source_order.total_amount)
        self.assertEqual(order.items.get().product_name, self.product.name)
        self.assertEqual(order.items.get().qty, 1)

    def test_out_of_stock_item_blocks_charge_before_payment(self):
        self.variant.stock_qty = 0
        self.variant.save(update_fields=["stock_qty"])
        charge = RecurringCharge.objects.create(
            recurring_order=self.plan,
            scheduled_for=self.plan.next_charge_at,
        )

        with self.assertRaisesMessage(ValueError, "Недостаточный остаток"):
            _create_order_for_recurring_charge(charge)

        charge.refresh_from_db()
        self.assertIsNone(charge.order)
