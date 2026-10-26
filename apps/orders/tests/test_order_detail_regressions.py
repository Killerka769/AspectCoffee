from decimal import Decimal
from unittest.mock import patch

from django.contrib.admin.sites import AdminSite
from django.test import TestCase
from django.urls import reverse

from apps.orders.admin import OrderAdmin
from apps.orders.models import Order, OrderItem
from apps.orders.tasks import create_cdek_waybill, send_order_confirmation
from apps.users.models import User


class OrderDetailRegressionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="order-detail@example.com",
            password="Strongpass1",
        )
        self.order = Order.objects.create(
            user=self.user,
            status=Order.STATUS_COMPLETED,
            delivery_type=Order.DELIVERY_CDEK_DOOR,
            delivery_address={
                "city": "Москва",
                "street": "Новая",
                "house": "1",
                "apartment": "",
            },
            delivery_cost=Decimal("635.00"),
            payment_method=Order.PAYMENT_CARD,
            payment_status=Order.PAYMENT_STATUS_PAID,
            total_amount=Decimal("1006.67"),
            contact_name="Иван Иванов",
            contact_phone="+79013573577",
            contact_email=self.user.email,
            recipient_name="Петр Петров",
            recipient_phone="+79995554433",
        )

    def test_account_detail_shows_actual_recipient_and_reorder_action(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("users:order_detail", args=[self.order.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Петр Петров")
        self.assertContains(response, "+79995554433")
        self.assertContains(response, "д. 1")
        self.assertContains(response, "Повторить заказ")
        self.assertContains(response, "Не включена в сумму оплаты")

    def test_admin_exposes_repeat_order_action(self):
        model_admin = OrderAdmin(Order, AdminSite())
        self.assertIn("repeat_in_customer_cart", model_admin.actions)
        self.assertEqual(model_admin.recipient_display(self.order), "Петр Петров")

    def test_detail_preserves_item_snapshot_after_catalog_variant_is_deleted(self):
        OrderItem.objects.create(order=self.order, variant=None, product_name="Исторический кофе", variant_description="250 г · для фильтра", qty=2, price_at_order=Decimal("500.00"))
        self.client.force_login(self.user)
        response = self.client.get(reverse("users:order_detail", args=[self.order.pk]))
        self.assertContains(response, "Исторический кофе")
        self.assertContains(response, "250 г · для фильтра")
        self.assertContains(response, "2 шт")
        self.assertContains(response, "1000")

    def test_detail_displays_full_pickup_address(self):
        self.order.delivery_type = Order.DELIVERY_CDEK_PVZ
        self.order.cdek_pvz_address = "Москва, Полная улица, 42, пункт выдачи"
        self.order.cdek_pvz_code = "MSK-42"
        self.order.save()
        self.client.force_login(self.user)
        response = self.client.get(reverse("users:order_detail", args=[self.order.pk]))
        self.assertContains(response, self.order.cdek_pvz_address)
        self.assertContains(response, "MSK-42")

    def test_customer_cannot_view_another_customers_order(self):
        stranger = User.objects.create_user(email="other@example.com", password="Strongpass1")
        self.client.force_login(stranger)
        self.assertEqual(self.client.get(reverse("users:order_detail", args=[self.order.pk])).status_code, 404)

    @patch("apps.users.notifications.send_logged_email")
    def test_pending_online_payment_email_does_not_claim_success(self, send_email):
        send_email.return_value.success = True
        self.order.status = Order.STATUS_NEW
        self.order.payment_status = Order.PAYMENT_STATUS_PENDING
        self.order.save(update_fields=["status", "payment_status"])

        send_order_confirmation.run(self.order.pk)

        call = send_email.call_args.kwargs
        self.assertEqual(call["subject"], f"Заказ #{self.order.pk} ожидает оплаты")
        self.assertIn("создан и ожидает оплаты", call["body"])
        self.assertNotIn("успешно оформлен", call["body"])

    @patch("apps.users.notifications.send_logged_email")
    def test_paid_online_payment_email_can_confirm_success(self, send_email):
        send_email.return_value.success = True

        send_order_confirmation.run(self.order.pk)

        call = send_email.call_args.kwargs
        self.assertEqual(call["subject"], f"Заказ #{self.order.pk} принят")
        self.assertIn("успешно оформлен", call["body"])

    @patch("apps.delivery.cdek.CDEKClient.create_order")
    def test_cdek_waybill_task_is_idempotent(self, create_order):
        self.order.cdek_order_uuid = "7d96f62d-f87d-4dbb-9fa6-1eca1e5a21ed"
        self.order.save(update_fields=["cdek_order_uuid"])

        result = create_cdek_waybill.run(self.order.pk)

        self.assertEqual(result, str(self.order.cdek_order_uuid))
        create_order.assert_not_called()

    @patch("apps.delivery.cdek.CDEKClient.create_order")
    def test_cdek_waybill_task_saves_created_uuid(self, create_order):
        create_order.return_value = {
            "entity": {"uuid": "017fbbda-0cea-4791-80a1-03150af453ea"},
        }

        result = create_cdek_waybill.run(self.order.pk)

        self.order.refresh_from_db()
        self.assertEqual(result, "017fbbda-0cea-4791-80a1-03150af453ea")
        self.assertEqual(str(self.order.cdek_order_uuid), result)
        create_order.assert_called_once()
