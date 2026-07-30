from django.test import TestCase
from django.urls import reverse

from apps.catalog.models import PromoSlide
from apps.pages.models import Banner


class HomeCarouselRegressionTests(TestCase):
    def test_weekly_banner_records_are_not_mixed_into_promo_slide_carousel(self):
        PromoSlide.objects.create(
            section_label="Журнал о кофе",
            title="Разрешённый промо-слайд",
            order=0,
            is_active=True,
        )
        Banner.objects.create(
            slot="home_weekly",
            title="Посторонний баннер",
            description="Не должен появляться в карусели промо-слайдов",
            is_active=True,
        )

        response = self.client.get(reverse("catalog:index"))

        self.assertContains(response, "Разрешённый промо-слайд")
        self.assertNotContains(response, "Посторонний баннер")
