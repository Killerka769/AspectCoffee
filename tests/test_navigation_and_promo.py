import pytest
from django.urls import reverse
from apps.catalog.models import NavMenuItem, PromoSlide


@pytest.mark.django_db
def test_nav_menu_items_context_processor(client):
    # Clear database state
    NavMenuItem.objects.all().delete()

    # Create active and inactive menu items
    NavMenuItem.objects.create(title="Active Item 1", url="/url1", order=2, is_active=True)
    NavMenuItem.objects.create(title="Active Item 2", url="/url2", order=1, is_active=True)
    NavMenuItem.objects.create(title="Inactive Item", url="/url3", order=3, is_active=False)

    # Get home page
    response = client.get(reverse("catalog:index"))
    assert response.status_code == 200

    # Verify context and ordering (order=1 should come first)
    assert "nav_menu_items" in response.context
    items_in_context = response.context["nav_menu_items"]
    assert len(items_in_context) == 2
    assert items_in_context[0].title == "Active Item 2"
    assert items_in_context[1].title == "Active Item 1"


@pytest.mark.django_db
def test_promo_slides_in_index_context(client):
    # Clear database state
    PromoSlide.objects.all().delete()

    # Create active and inactive promo slides
    PromoSlide.objects.create(
        section_label="Section 1",
        title="Active Slide 1",
        order=2,
        is_active=True
    )
    PromoSlide.objects.create(
        section_label="Section 2",
        title="Active Slide 2",
        order=1,
        is_active=True
    )
    PromoSlide.objects.create(
        section_label="Section 3",
        title="Inactive Slide",
        order=3,
        is_active=False
    )

    response = client.get(reverse("catalog:index"))
    assert response.status_code == 200

    # Verify context and ordering
    assert "promo_slides" in response.context
    slides_in_context = response.context["promo_slides"]
    assert len(slides_in_context) == 2
    assert slides_in_context[0].title == "Active Slide 2"
    assert slides_in_context[1].title == "Active Slide 1"
