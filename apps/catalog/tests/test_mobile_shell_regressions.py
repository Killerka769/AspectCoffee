from pathlib import Path
from bs4 import BeautifulSoup
from django.conf import settings
from django.test import TestCase


class MobileShellRegressionTests(TestCase):
    def test_bottom_navigation_matches_accepted_four_tab_redesign(self):
        response = self.client.get("/")
        nav = BeautifulSoup(response.content, "html.parser").select_one("#mob-bottom-nav")
        self.assertIsNotNone(nav)
        labels = [link.get_text(" ", strip=True) for link in nav.select("a")]
        self.assertEqual(labels, ["Главная", "Каталог", "Избранное", "Вход"])
        self.assertFalse(any("basket" in link.get("href", "") for link in nav.select("a")))

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
        self.assertNotContains(self.client.get("/catalog/"), 'data-testid="mobile-catalog-reset"')
        self.assertContains(self.client.get("/catalog/?acidity=medium"), 'data-testid="mobile-catalog-reset"')

    def test_product_tabs_allow_horizontal_scrolling(self):
        template = (Path(settings.BASE_DIR) / "apps/catalog/templates/catalog/detail.html").read_text(encoding="utf-8")
        self.assertIn("overflow-x: auto", template)

    def test_compare_state_still_synchronizes_after_action(self):
        js = (Path(settings.BASE_DIR) / "static/asset/js/custom.js").read_text(encoding="utf-8")
        self.assertNotIn("showCompareBar", js)
        stored = js.index("localStorage.setItem('compare', JSON.stringify(list));")
        dispatched = js.index("document.body.dispatchEvent(new CustomEvent('compareUpdated'", stored)
        self.assertGreater(dispatched, stored)
