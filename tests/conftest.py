
"""
tests/conftest.py — Global test fixtures with external API mocking.
Fix #6v3: all external services (YooKassa, CDEK) are mocked to prevent
tests from requiring internet access or real API keys.
"""
import pytest
from unittest.mock import MagicMock
from django.test import RequestFactory
from types import SimpleNamespace


class MockYooKassaPayment:
    id = "test-payment-id-12345"
    status = "pending"
    confirmation = MagicMock()

    def __init__(self):
        self.confirmation.confirmation_url = "https://yookassa.ru/test-checkout"


class MockYooKassaRefund:
    id = "test-refund-id-67890"
    status = "succeeded"


@pytest.fixture(autouse=True)
def mock_yookassa(monkeypatch):
    """Mock all YooKassa SDK calls."""
    monkeypatch.setattr(
        "yookassa.Payment.create",
        lambda *args, **kwargs: MockYooKassaPayment(),
    )
    monkeypatch.setattr(
        "yookassa.Refund.create",
        lambda *args, **kwargs: MockYooKassaRefund(),
    )

    def verified_payment(payment_id):
        from apps.payments.models import Payment

        payment = Payment.objects.select_related("order").get(
            yookassa_id=payment_id
        )
        status = "pending" if "pending" in payment_id else "succeeded"
        return SimpleNamespace(
            id=payment_id,
            status=status,
            amount=SimpleNamespace(value=str(payment.amount)),
            metadata={"order_id": str(payment.order_id)},
            payment_method=None,
        )

    # Both modules hold their own imported reference to the verifier.
    monkeypatch.setattr(
        "apps.payments.services.fetch_yookassa_payment",
        verified_payment,
    )
    monkeypatch.setattr(
        "apps.payments.views.fetch_yookassa_payment",
        verified_payment,
    )


@pytest.fixture(autouse=True)
def mock_cdek(monkeypatch):
    """Mock CDEK API calls."""
    monkeypatch.setattr(
        "apps.delivery.cdek.CDEKClient.calc_tariff_preview",
        lambda self, *args, **kwargs: {"tariffs": [], "error": None},
    )
    monkeypatch.setattr(
        "apps.delivery.cdek.CDEKClient.create_order",
        lambda self, *args, **kwargs: {"entity": {"uuid": "test-uuid"}},
    )
    monkeypatch.setattr(
        "apps.delivery.cdek.CDEKClient.get_order",
        lambda self, *args, **kwargs: {"entity": {"cdek_number": ""}},
    )


@pytest.fixture(autouse=True)
def mock_celery_tasks(monkeypatch):
    """Make Celery tasks run synchronously (not via broker) in tests."""
    from unittest.mock import patch
    monkeypatch.setattr(
        "apps.orders.tasks.send_order_confirmation.delay",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "apps.orders.tasks.send_order_status_email.delay",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "apps.payments.tasks.check_payment_timeout.apply_async",
        lambda *args, **kwargs: None,
    )


@pytest.fixture
def api_client():
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def user(db):
    from apps.users.models import User
    return User.objects.create_user(
        email="test@example.com",
        password="testpass123",
        first_name="Test",
        last_name="User",
        email_confirmed=True,
    )


@pytest.fixture
def wholesale_user(db):
    from apps.users.models import User
    return User.objects.create_user(
        email="wholesale@example.com",
        password="testpass123",
        role=User.ROLE_WHOLESALE,
        email_confirmed=True,
        company_inn="1234567890",
    )


@pytest.fixture
def warehouse_user(db):
    from apps.users.models import User
    return User.objects.create_user(
        email="warehouse@example.com",
        password="testpass123",
        role=User.ROLE_WAREHOUSE,
        email_confirmed=True,
    )
