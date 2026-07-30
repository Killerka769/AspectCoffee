from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib import admin
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory, TestCase, override_settings
from django.utils import timezone

from apps.catalog.models import Product, ProductVariant, SiteSettings
from apps.orders.admin import RecurringChargeAdmin, RecurringOrderAdmin
from apps.orders.models import Order, OrderItem, RecurringCharge, RecurringOrder
from apps.orders.recurring import recurring_payments_enabled
from apps.users.models import User


class RecurringAdminTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            email="recurring-admin@example.com",
            password="StrongPass1",
        )
        self.customer = User.objects.create_user(
            email="recurring-customer@example.com",
            password="StrongPass1",
        )
        product = Product.objects.create(name="Кофе для автоповтора", slug="recurring-coffee")
        variant = ProductVariant.objects.create(
            product=product,
            weight=250,
            price=Decimal("627.00"),
            stock_qty=20,
        )
        self.order = Order.objects.create(
            user=self.customer,
            delivery_type=Order.DELIVERY_CDEK_PVZ,
            payment_method=Order.PAYMENT_CARD,
            total_amount=Decimal("627.00"),
            contact_name="Покупатель",
            contact_phone="+79990000000",
            contact_email=self.customer.email,
        )
        OrderItem.objects.create(
            order=self.order,
            variant=variant,
            product_name=product.name,
            variant_description="250 г",
            qty=1,
            price_at_order=variant.price,
        )
        self.plan = RecurringOrder.objects.create(
            source_order=self.order,
            user=self.customer,
            interval_weeks=2,
            saved_payment_method_id="saved-method-test",
        )
        self.factory = RequestFactory()

    def admin_request(self):
        request = self.factory.post("/admin/orders/")
        request.user = self.admin_user
        request.session = {}
        request._messages = FallbackStorage(request)
        return request

    def test_admin_can_activate_pause_and_cancel_plan(self):
        model_admin = RecurringOrderAdmin(RecurringOrder, admin.site)
        queryset = RecurringOrder.objects.filter(pk=self.plan.pk)

        model_admin.activate_selected(self.admin_request(), queryset)
        self.plan.refresh_from_db()
        self.assertEqual(self.plan.status, RecurringOrder.STATUS_ACTIVE)
        self.assertIsNotNone(self.plan.next_charge_at)

        model_admin.pause_selected(self.admin_request(), queryset)
        self.plan.refresh_from_db()
        self.assertEqual(self.plan.status, RecurringOrder.STATUS_PAUSED)

        model_admin.cancel_selected(self.admin_request(), queryset)
        self.plan.refresh_from_db()
        self.assertEqual(self.plan.status, RecurringOrder.STATUS_CANCELLED)
        self.assertIsNone(self.plan.next_charge_at)

    @patch("apps.payments.tasks.process_recurring_charge.delay")
    def test_admin_can_queue_immediate_charge(self, delay):
        self.plan.status = RecurringOrder.STATUS_ACTIVE
        self.plan.next_charge_at = timezone.now() + timedelta(weeks=2)
        self.plan.save(update_fields=["status", "next_charge_at"])

        model_admin = RecurringOrderAdmin(RecurringOrder, admin.site)
        model_admin.charge_now(
            self.admin_request(),
            RecurringOrder.objects.filter(pk=self.plan.pk),
        )

        charge = RecurringCharge.objects.get(recurring_order=self.plan)
        delay.assert_called_once_with(charge.pk)

    @patch("apps.payments.tasks.process_recurring_charge.delay")
    def test_admin_can_retry_failed_charge(self, delay):
        self.plan.status = RecurringOrder.STATUS_PAUSED
        self.plan.save(update_fields=["status"])
        charge = RecurringCharge.objects.create(
            recurring_order=self.plan,
            scheduled_for=timezone.now(),
            status=RecurringCharge.STATUS_FAILED,
            error_message="Сбой шлюза",
        )

        model_admin = RecurringChargeAdmin(RecurringCharge, admin.site)
        model_admin.retry_failed(
            self.admin_request(),
            RecurringCharge.objects.filter(pk=charge.pk),
        )

        self.plan.refresh_from_db()
        charge.refresh_from_db()
        self.assertEqual(self.plan.status, RecurringOrder.STATUS_ACTIVE)
        self.assertEqual(charge.status, RecurringCharge.STATUS_PENDING)
        self.assertEqual(charge.error_message, "")
        delay.assert_called_once_with(charge.pk)

    @override_settings(YOOKASSA_RECURRENT_ENABLED=True)
    def test_global_admin_switch_disables_recurring_payments(self):
        SiteSettings.objects.update_or_create(
            pk=1,
            defaults={"recurring_payments_enabled": False},
        )
        self.assertFalse(recurring_payments_enabled())
