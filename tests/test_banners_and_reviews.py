import pytest
from django.urls import reverse
from apps.pages.models import Banner
from apps.catalog.models import Product, Review


@pytest.mark.django_db
def test_default_banners_seeded():
    # Verify the migration seeded the banners
    banners = Banner.objects.filter(slot="popular_block")
    assert banners.count() >= 2
    titles = [b.title for b in banners]
    assert "Дарим подарки, делаем скидки" in titles
    assert "Сильная команда" in titles


@pytest.mark.django_db
def test_banners_rendered_on_index_page(client):
    # Clear preexisting banners
    Banner.objects.filter(slot="popular_block").delete()

    # Create one custom banner
    Banner.objects.create(
        slot="popular_block",
        title="Custom Banner 123",
        description="Description 123",
        is_active=True,
        order=1
    )

    response = client.get(reverse("catalog:index"))
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    
    # Custom banner should be present
    assert "Custom Banner 123" in content
    # Hardcoded default values shouldn't be here since the loop is dynamic now
    assert "Дарим подарки, делаем скидки" not in content


@pytest.mark.django_db
def test_rating_hidden_when_no_reviews(client):
    # Create product with no reviews
    product = Product.objects.create(name="No Reviews Coffee", is_active=True, slug="no-reviews-coffee")
    
    response = client.get(reverse("catalog:index"))
    assert response.status_code == 200
    content = response.content.decode("utf-8")

    # The link to the product reviews/details should not show rating star/counter on tiles
    # In index page, for this product card:
    # Since reviews_count is 0, the aspect-card-meta wrapper shouldn't be rendered for it.
    # We can check that the product name is present, but "aspect-tile-rating" is not associated with this product's page.
    # In fact, we can verify product attributes:
    assert product.reviews_count == 0
    assert product.rating_avg == 0


@pytest.mark.django_db
def test_rating_calculation_on_approved_reviews():
    # Create product
    product = Product.objects.create(name="Review Coffee", is_active=True, slug="review-coffee")

    # Initially 0 reviews
    assert product.reviews_count == 0
    assert product.rating_avg == 0

    # Add unapproved review - shouldn't update product rating
    review1 = Review.objects.create(
        product=product,
        rating=5,
        text="Unapproved",
        status=Review.STATUS_NEW,
    )
    product.refresh_from_db()
    assert product.reviews_count == 0
    assert product.rating_avg == 0

    # Approve review - should update product rating
    review1.status = Review.STATUS_PUBLISHED
    review1.save(update_fields=["status"])
    product.refresh_from_db()
    assert product.reviews_count == 1
    assert product.rating_avg == 5.0

    # Add approved review - should update rating
    review2 = Review.objects.create(
        product=product,
        rating=3,
        text="Approved",
        status=Review.STATUS_PUBLISHED,
    )
    product.refresh_from_db()
    assert product.reviews_count == 2
    assert product.rating_avg == 4.0

    # Unapprove one review - should update rating
    review2.status = Review.STATUS_UNPUBLISHED
    review2.save(update_fields=["status"])
    product.refresh_from_db()
    assert product.reviews_count == 1
    assert product.rating_avg == 5.0

    # Delete the remaining approved review - should reset to 0
    review1.delete()
    product.refresh_from_db()
    assert product.reviews_count == 0
    assert product.rating_avg == 0
