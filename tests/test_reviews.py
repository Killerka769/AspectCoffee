"""Tests for the product review endpoint auth fix.

Bug (image20): a Django session-authenticated user got 401 when posting a
review because DRF only had JWTAuthentication enabled. The `reviews` action
now also accepts SessionAuthentication.
"""
import pytest


@pytest.fixture
def product(db):
    from apps.catalog.models import Product
    return Product.objects.create(name="Тестовый кофе ревью", is_active=True)


@pytest.mark.django_db
def test_review_post_requires_auth(api_client, product):
    resp = api_client.post(
        f"/api/v1/catalog/products/{product.slug}/reviews/",
        {"rating": 5, "text": "Отлично"},
        format="json",
    )
    assert resp.status_code == 401


@pytest.mark.django_db
def test_review_post_with_session_auth(api_client, user, product):
    assert api_client.login(email="test@example.com", password="testpass123")
    resp = api_client.post(
        f"/api/v1/catalog/products/{product.slug}/reviews/",
        {"rating": 5, "text": "Отличный кофе, рекомендую"},
        format="json",
    )
    assert resp.status_code == 201, resp.content
    from apps.catalog.models import Review
    assert Review.objects.filter(product=product, user=user).exists()
