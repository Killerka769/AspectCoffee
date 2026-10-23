from django.test import TestCase

from apps.catalog.models import Category, NavMenuItem
from apps.users.models import User


class MobileMenuTests(TestCase):
    def test_mobile_menu_preserves_configured_and_hardcoded_order(self):
        Category.objects.create(name="Вторая категория", slug="second", order=20)
        Category.objects.create(name="Первая категория", slug="first", order=10)
        NavMenuItem.objects.create(title="Вторая ссылка", url="/second-link/", order=20)
        NavMenuItem.objects.create(title="Первая ссылка", url="/first-link/", order=10)

        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        html = response.content.decode("utf-8")
        start = html.index('<aside class="aspect-mobile-menu"')
        end = html.index("</aside>", start)
        menu = html[start:end]

        ordered_labels = (
            "Купить",
            "Первая категория",
            "Вторая категория",
            "Первая ссылка",
            "Вторая ссылка",
            "Отзывы",
            "Сообщество",
            "Журнал",
            "Условия",
            "Доставка и оплата",
            "Система скидок",
            "Возврат денег",
            "Частые вопросы",
            "Как приготовить кофе",
        )
        positions = [menu.index(label) for label in ordered_labels]
        self.assertEqual(positions, sorted(positions))

    def test_mobile_menu_has_close_button_and_conditional_cdek_block(self):
        response = self.client.get("/")
        html = response.content.decode("utf-8")

        self.assertContains(response, 'class="aspect-mobile-menu__close"')
        self.assertContains(response, 'aria-label="Закрыть меню"')
        self.assertContains(response, 'class="aspect-backdrop"')
        self.assertContains(response, 'x-show="menuOpen || searchOpen || cartOpen"')

    def test_authenticated_account_actions_keep_reading_order(self):
        user = User.objects.create_user(email="mobile-menu@example.com", password="test-pass-123")
        self.client.force_login(user)

        response = self.client.get("/")
        html = response.content.decode("utf-8")
        start = html.index('<aside class="aspect-mobile-menu"')
        end = html.index("</aside>", start)
        menu = html[start:end]

        profile = menu.index("Профиль")
        discount = menu.index("Скидка")
        logout = menu.index("Выйти")
        self.assertLess(profile, discount)
        self.assertLess(discount, logout)
