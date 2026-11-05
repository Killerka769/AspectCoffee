from pathlib import Path
from django.conf import settings
from django.test import TestCase


class MobileShellRegressionTests(TestCase):
    def test_bottom_navigation_is_not_duplicated_under_the_header(self):
        response = self.client.get("/")
        self.assertNotContains(response, 'id="mob-bottom-nav"')
        self.assertNotContains(response, "mob-bottom-nav__item")

    def test_search_closes_other_mobile_panels(self):
        response = self.client.get("/")
        self.assertContains(response, "menuOpen = false; searchOpen = true; cartOpen = false; wishlistOpen = false; notifOpen = false;")

    def test_backdrop_and_escape_close_panels(self):
        response = self.client.get("/")
        self.assertContains(response, 'class="aspect-backdrop"')
        self.assertContains(response, 'x-show="menuOpen || searchOpen || cartOpen"')
        self.assertContains(response, "@keydown.escape.window")

    def test_accepted_brand_assets_are_loaded(self):
        response = self.client.get("/")
        self.assertContains(response, "aspect-brand.css")
        self.assertContains(response, "aspect-redesign.css")
        self.assertContains(response, "logo-aspect.svg")

    def test_catalog_reset_is_bound_to_active_query(self):
        self.assertNotContains(self.client.get("/catalog/"), 'data-catalog-reset="1"')
        self.assertContains(self.client.get("/catalog/?acidity=medium"), 'data-catalog-reset="1"')

    def test_product_tabs_allow_horizontal_scrolling(self):
        template = (Path(settings.BASE_DIR) / "apps/catalog/templates/catalog/detail.html").read_text(encoding="utf-8")
        self.assertIn("overflow-x: auto", template)

    def test_compare_state_still_synchronizes_after_action(self):
        js = (Path(settings.BASE_DIR) / "static/asset/js/custom.js").read_text(encoding="utf-8")
        self.assertNotIn("showCompareBar", js)
        stored = js.index("localStorage.setItem('compare', JSON.stringify(list));")
        dispatched = js.index("document.body.dispatchEvent(new CustomEvent('compareUpdated'", stored)
        self.assertGreater(dispatched, stored)
