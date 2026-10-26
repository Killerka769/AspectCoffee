from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.test import SimpleTestCase


class AdminLocalizationTests(SimpleTestCase):
    def test_russian_locale_and_admin_translation_assets_are_enabled(self):
        self.assertEqual(settings.LANGUAGE_CODE, "ru-ru")
        self.assertIn("django.middleware.locale.LocaleMiddleware", settings.MIDDLEWARE)
        self.assertIn(Path(settings.BASE_DIR) / "locale", settings.LOCALE_PATHS)

        script_path = Path(settings.BASE_DIR) / "static/asset/js/admin_ru.js"
        script = script_path.read_text(encoding="utf-8")
        for source, translated in (
            ("Search apps and models...", "Поиск приложений и моделей..."),
            ("Select action", "Выберите действие"),
            ("Type to search", "Начните вводить для поиска"),
            ("All applications", "Все приложения"),
            ("Token Blacklist", "Токены доступа"),
        ):
            self.assertIn(source, script)
            self.assertIn(translated, script)
        self.assertIn("if (translated !== current)", script)
        self.assertNotIn("root.nodeValue = translateValue(root.nodeValue)", script)

    def test_local_admin_models_and_fields_have_russian_labels(self):
        expected_models = {
            "pages.CommunityPostComment": "Комментарий сообщества",
            "pages.ReviewComment": "Комментарий к отзыву",
            "blog.ArticleLike": "Отметка «нравится» у статьи",
        }
        for label, verbose_name in expected_models.items():
            self.assertEqual(str(apps.get_model(label)._meta.verbose_name), verbose_name)

        expected_fields = {
            "catalog.SiteSettings.contact_email": "Email сайта для заявок",
            "users.BonusTransaction.order": "Заказ",
            "orders.Cart.created_at": "Создана",
            "catalog.Category.created_at": "Создана",
            "blog.BlogCategory.slug": "Адрес в URL",
        }
        for dotted_path, verbose_name in expected_fields.items():
            app_label, model_name, field_name = dotted_path.split(".")
            field = apps.get_model(app_label, model_name)._meta.get_field(field_name)
            self.assertEqual(str(field.verbose_name), verbose_name)
