from django.test import TestCase
from django.urls import reverse

from apps.users.models import Achievement, User


class AchievementIconTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="achievement-icons@example.com",
            password="test-pass-123",
        )
        self.client.force_login(self.user)

    def test_default_icons_are_rendered_for_all_seeded_achievements(self):
        icons_by_title = {
            "Первый заказ": "achievement-first-order-transparent.webp",
            "Кофеман": "achievement-coffee-lover-transparent.webp",
            "Знаток кофе": "achievement-coffee-expert-transparent.webp",
            "VIP-клиент": "achievement-vip-client-transparent.webp",
            "Любитель скидок": "achievement-discount-lover-transparent.webp",
            "Коллекционер": "achievement-collector-transparent.webp",
            "Миллионер": "achievement-millionaire-transparent.webp",
        }
        for sort_order, title in enumerate(icons_by_title):
            Achievement.objects.create(
                title=title,
                condition_type="orders_count",
                condition_value=100,
                sort_order=sort_order,
            )

        response = self.client.get(reverse("users:achievements"))

        self.assertEqual(response.status_code, 200)
        for filename in icons_by_title.values():
            self.assertContains(
                response,
                f'/static/asset/images/achievements/{filename}',
            )
        self.assertNotContains(response, "group-hover:-top-6")

    def test_uploaded_icon_has_priority_over_default_icon(self):
        achievement = Achievement.objects.create(
            title="Первый заказ",
            condition_type="orders_count",
            condition_value=100,
        )
        achievement.icon.name = "achievements/custom-first-order.png"
        achievement.save(update_fields=["icon"])

        response = self.client.get(reverse("users:achievements"))

        self.assertContains(response, "/media/achievements/custom-first-order.png")
        self.assertNotContains(response, "achievement-first-order-transparent.webp")
