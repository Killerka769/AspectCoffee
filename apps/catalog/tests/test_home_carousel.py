from django.test import TestCase
from django.urls import reverse

from apps.catalog.models import PromoSlide


class HomeCarouselRegressionTests(TestCase):
    def test_weekly_banner_records_are_not_mixed_into_promo_slide_carousel(self):
        PromoSlide.objects.create(
            section_label="Журнал о кофе",
            title="Разрешённый промо-слайд",
            order=0,
            is_active=True,
        )
        PromoSlide.objects.create(
            section_label="Неактивное предложение",
            title="Посторонний баннер",
            is_active=False,
        )

        response = self.client.get(reverse("catalog:index"))

        self.assertContains(response, "Разрешённый промо-слайд")
        self.assertNotContains(response, "Посторонний баннер")
