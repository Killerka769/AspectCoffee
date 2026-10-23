from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.test import SimpleTestCase


class RedesignPreservationTests(SimpleTestCase):
    def test_accepted_redesign_assets_and_templates_remain_in_release(self):
        root = Path(settings.BASE_DIR)
        self.assertTrue((root / "static/css/aspect-redesign.css").is_file())
        self.assertTrue((root / "static/asset/images/logo-aspect.svg").is_file())
        templates = {
            "apps/pages/templates/pages/contact_us.html": "aspect-contact__",
            "apps/pages/templates/pages/partners.html": "aspect-partners__",
            "apps/users/templates/users/login.html": "aspect-auth__",
            "apps/users/templates/users/order_detail.html": "asp-od__",
            "apps/orders/templates/orders/basket.html": "ckc-",
        }
        for path, marker in templates.items():
            self.assertIn(marker, (root / path).read_text(encoding="utf-8"))

    def test_retired_catalog_and_content_models_are_not_resurrected(self):
        labels = {model._meta.label_lower for model in apps.get_models()}
        for label in ("catalog.recipe", "catalog.recipestep", "catalog.tag", "catalog.roaster", "pages.banner", "blog.articlereadhistory"):
            self.assertNotIn(label, labels)
