from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from apps.orders.models import Order, RecurringOrder
from apps.payments.models import Payment
from apps.payments.services import apply_verified_payment
from apps.users.models import User


class PaymentReconciliationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="payment-check@example.com",
            password="Strongpass1",
        )
        self.order = Order.objects.create(
            user=self.user,
            status=Order.STATUS_NEW,
            delivery_type=Order.DELIVERY_CDEK_DOOR,
            delivery_address={"city": "Москва", "street": "Новая", "house": "1"},
            delivery_cost=Decimal("635.00"),
            payment_method=Order.PAYMENT_CARD,
            payment_status=Order.PAYMENT_STATUS_PENDING,
            total_amount=Decimal("1641.67"),
            contact_name="Иван",
            contact_phone="+79000000000",
            contact_email=self.user.email,
        )
        self.payment = Payment.objects.create(
            order=self.order,
            yookassa_id="payment-test-1",
            amount=self.order.total_amount,
            status=Payment.STATUS_PENDING,
        )

    @patch("apps.orders.tasks.create_cdek_waybill.delay")
    @patch("apps.orders.tasks.send_order_status_email.delay")
    def test_succeeded_payment_updates_order_and_queues_follow_up(self, email_delay, cdek_delay):
        result = apply_verified_payment(
            self.payment.yookassa_id,
            "succeeded",
            self.order.pk,
            self.order.total_amount,
        )

        self.payment.refresh_from_db()
        self.order.refresh_from_db()
        self.assertTrue(result["updated"])
        self.assertEqual(self.payment.status, Payment.STATUS_SUCCEEDED)
        self.assertEqual(self.order.payment_status, Order.PAYMENT_STATUS_PAID)
        self.assertEqual(self.order.status, Order.STATUS_PAID)
        self.assertEqual(self.order.payment_id, self.payment.yookassa_id)
        email_delay.assert_called_once_with(self.order.pk, Order.STATUS_PAID)
        cdek_delay.assert_called_once_with(self.order.pk)

    @patch("apps.orders.tasks.create_cdek_waybill.delay")
    @patch("apps.orders.tasks.send_order_status_email.delay")
    def test_reconciliation_does_not_regress_completed_order(self, email_delay, cdek_delay):
        self.order.status = Order.STATUS_COMPLETED
        self.order.save(update_fields=["status"])

        apply_verified_payment(
            self.payment.yookassa_id,
            "succeeded",
            self.order.pk,
            self.order.total_amount,
        )

        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.STATUS_COMPLETED)
        self.assertEqual(self.order.payment_status, Order.PAYMENT_STATUS_PAID)
        email_delay.assert_not_called()
        cdek_delay.assert_not_called()

    def test_amount_mismatch_never_marks_order_paid(self):
        result = apply_verified_payment(
            self.payment.yookassa_id,
            "succeeded",
            self.order.pk,
            Decimal("1.00"),
        )

        self.payment.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(result["reason"], "amount_mismatch")
        self.assertEqual(self.payment.status, Payment.STATUS_PENDING)
        self.assertEqual(self.order.payment_status, Order.PAYMENT_STATUS_PENDING)
        self.assertEqual(self.order.status, Order.STATUS_NEW)

    @patch("apps.orders.tasks.create_cdek_waybill.delay")
    @patch("apps.orders.tasks.send_order_status_email.delay")
    def test_success_activates_recurring_plan_only_with_saved_method(self, _email, _cdek):
        plan = RecurringOrder.objects.create(
            source_order=self.order,
            user=self.user,
            interval_weeks=2,
        )

        apply_verified_payment(
            self.payment.yookassa_id,
            "succeeded",
            self.order.pk,
            self.order.total_amount,
            "saved-method-1",
            True,
            "bank_card",
            "4242",
        )

        plan.refresh_from_db()
        self.payment.refresh_from_db()
        self.assertEqual(plan.status, RecurringOrder.STATUS_ACTIVE)
        self.assertEqual(plan.saved_payment_method_id, "saved-method-1")
        self.assertIsNotNone(plan.next_charge_at)
        self.assertTrue(self.payment.payment_method_saved)
        self.assertEqual(self.payment.card_last4, "4242")
