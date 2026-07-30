
"""
tests/test_payments.py — Payment system tests.
All external APIs are mocked via conftest.py fixtures.
"""
import pytest
from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch, MagicMock


@pytest.mark.django_db
class TestPaymentWebhookIdempotency:
    """
    Fix #2v3 verification: webhook processed twice should not double-mark order as paid.
    """

    def _make_order(self, user):
        from apps.orders.models import Order
        return Order.objects.create(
            user=user,
            delivery_type=Order.DELIVERY_PICKUP,
            delivery_address={},
            payment_method=Order.PAYMENT_CARD,
            contact_name="Test User",
            contact_phone="+70000000000",
            contact_email=user.email,
            total_amount="1000.00",
        )

    def test_webhook_idempotency_double_call(self, api_client, user):
        """Sending same webhook twice should not change order status twice."""
        from apps.payments.models import Payment

        order = self._make_order(user)
        payment = Payment.objects.create(
            order=order,
            yookassa_id="test-payment-abc123",
            amount="1000.00",
            status=Payment.STATUS_PENDING,
        )

        webhook_data = {
            "event": "payment.succeeded",
            "object": {
                "id": "test-payment-abc123",
                "status": "succeeded",
                "amount": {"value": "1000.00", "currency": "RUB"},
            }
        }

        response1 = api_client.post(
            "/api/v1/payments/webhook/",
            data=webhook_data,
            format="json",
        )
        assert response1.status_code == 200

        payment.refresh_from_db()
        assert payment.status == Payment.STATUS_SUCCEEDED

        response2 = api_client.post(
            "/api/v1/payments/webhook/",
            data=webhook_data,
            format="json",
        )
        assert response2.status_code == 200

        payment.refresh_from_db()
        assert payment.status == Payment.STATUS_SUCCEEDED


@pytest.mark.django_db
class TestPaymentTimeoutGuard:
    """
    Fix #3v3 verification: timeout task must NOT cancel already-paid orders.
    """

    def test_timeout_does_not_cancel_paid_order(self, user):
        from apps.orders.models import Order
        from apps.payments.models import Payment
        from apps.payments.tasks import check_payment_timeout

        order = Order.objects.create(
            user=user,
            delivery_type=Order.DELIVERY_PICKUP,
            delivery_address={},
            payment_method=Order.PAYMENT_CARD,
            contact_name="Test User",
            contact_phone="+70000000000",
            contact_email=user.email,
            total_amount="1500.00",
            payment_status=Order.PAYMENT_STATUS_PAID,
            status=Order.STATUS_PAID,
        )
        payment = Payment.objects.create(
            order=order,
            yookassa_id="test-paid-payment",
            amount="1500.00",
            status=Payment.STATUS_SUCCEEDED,
        )

        check_payment_timeout(payment.id)

        order.refresh_from_db()
        assert order.status == Order.STATUS_PAID
        assert order.payment_status == Order.PAYMENT_STATUS_PAID

    def test_timeout_cancels_unpaid_order(self, user):
        from apps.orders.models import Order
        from apps.payments.models import Payment
        from apps.payments.tasks import check_payment_timeout

        order = Order.objects.create(
            user=user,
            delivery_type=Order.DELIVERY_PICKUP,
            delivery_address={},
            payment_method=Order.PAYMENT_CARD,
            contact_name="Test User",
            contact_phone="+70000000000",
            contact_email=user.email,
            total_amount="2000.00",
        )
        payment = Payment.objects.create(
            order=order,
            yookassa_id="test-pending-payment",
            amount="2000.00",
            status=Payment.STATUS_PENDING,
        )

        check_payment_timeout(payment.id)

        order.refresh_from_db()
        assert order.status == Order.STATUS_CANCELLED


@pytest.mark.django_db
class TestCancelOrderRefund:
    """
    Fix #5v3 verification: cancelling a paid order triggers refund task.
    """

    def test_cancel_paid_order_triggers_refund(self, client, user):
        from apps.orders.models import Order
        from apps.payments.models import Payment

        client.force_login(user)
        order = Order.objects.create(
            user=user,
            delivery_type=Order.DELIVERY_PICKUP,
            delivery_address={},
            payment_method=Order.PAYMENT_CARD,
            contact_name="Test User",
            contact_phone="+70000000000",
            contact_email=user.email,
            total_amount="3000.00",
            payment_status=Order.PAYMENT_STATUS_PAID,
            status=Order.STATUS_PAID,
        )
        Payment.objects.create(
            order=order,
            yookassa_id="test-cancel-refund",
            amount="3000.00",
            status="succeeded",
        )

        with patch("apps.payments.tasks.process_refund.delay") as mock_refund:
            response = client.post(f"/account/orders/{order.id}/cancel/")
            assert mock_refund.called, "process_refund.delay should be called for paid orders"

        order.refresh_from_db()
        assert order.status == Order.STATUS_CANCELLED


@pytest.mark.django_db
class TestPendingPaymentReturnFlow:
    def _make_pending_order(self, user, payment_id="test-pending-return"):
        from apps.orders.models import Order
        from apps.payments.models import Payment

        order = Order.objects.create(
            user=user,
            delivery_type=Order.DELIVERY_PICKUP,
            delivery_address={},
            payment_method=Order.PAYMENT_CARD,
            contact_name="Test User",
            contact_phone="+70000000000",
            contact_email=user.email if user else "guest@example.com",
            total_amount="1000.00",
        )
        Payment.objects.create(
            order=order,
            yookassa_id=payment_id,
            amount="1000.00",
            status=Payment.STATUS_PENDING,
            confirmation_url="https://yookassa.ru/test-checkout",
        )
        return order

    def test_back_from_yookassa_keeps_order_pending(self, client, user):
        from apps.orders.models import Order

        client.force_login(user)
        order = self._make_pending_order(user)

        response = client.get(reverse("orders:order_success", args=[order.pk]))

        assert response.status_code == 200
        body = response.content.decode("utf-8")
        assert "Заказ ожидает оплаты" in body
        assert "Вернуться к оплате" in body
        assert "Заказ оформлен!" not in body
        order.refresh_from_db()
        assert order.status == Order.STATUS_NEW
        assert order.payment_status == Order.PAYMENT_STATUS_PENDING

    def test_resume_redirects_to_existing_yookassa_payment(self, client, user):
        client.force_login(user)
        order = self._make_pending_order(user, payment_id="test-pending-resume")

        response = client.get(reverse("orders:resume_payment", args=[order.pk]))

        assert response.status_code == 302
        assert response.url == "https://yookassa.ru/test-checkout"

    def test_pending_payment_action_is_visible_in_account(self, client, user):
        client.force_login(user)
        order = self._make_pending_order(user, payment_id="test-pending-account")

        response = client.get(reverse("users:order_detail", args=[order.pk]))

        assert response.status_code == 200
        body = response.content.decode("utf-8")
        assert "Заказ ожидает оплаты" in body
        assert "Вернуться к оплате" in body

    def test_another_user_cannot_open_or_resume_payment(self, client, user):
        from apps.users.models import User

        order = self._make_pending_order(user, payment_id="test-pending-private")
        other = User.objects.create_user(
            email="other@example.com",
            password="testpass123",
        )
        client.force_login(other)

        success_response = client.get(
            reverse("orders:order_success", args=[order.pk])
        )
        resume_response = client.get(
            reverse("orders:resume_payment", args=[order.pk])
        )

        assert success_response.status_code == 302
        assert resume_response.status_code == 302
        assert success_response.url == reverse("catalog:index")
        assert resume_response.url == reverse("catalog:index")

    def test_guest_order_requires_the_checkout_session(self, client):
        order = self._make_pending_order(None, payment_id="test-pending-guest")

        denied = client.get(reverse("orders:order_success", args=[order.pk]))
        assert denied.status_code == 302
        assert denied.url == reverse("catalog:index")

        session = client.session
        session["checkout_order_ids"] = [order.pk]
        session.save()

        allowed = client.get(reverse("orders:order_success", args=[order.pk]))
        assert allowed.status_code == 200
        assert "Заказ ожидает оплаты" in allowed.content.decode("utf-8")


def test_existing_account_checkout_block_is_shared_by_mobile_and_desktop():
    from pathlib import Path

    template = (
        Path(__file__).resolve().parents[1]
        / "apps"
        / "orders"
        / "templates"
        / "orders"
        / "basket.html"
    ).read_text(encoding="utf-8")

    assert template.count('name="register_account"') == 1
    assert template.index('name="register_account"') > template.index(
        'class="recipient-mobile'
    )
