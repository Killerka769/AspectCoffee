from pathlib import Path

from django.conf import settings
from django.test import TestCase


class MobileShellRegressionTests(TestCase):
    def test_bottom_navigation_uses_compare_instead_of_duplicate_cart(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="mob-nav-compare-badge"')
        self.assertNotContains(response, 'id="mob-nav-cart-badge"')
        self.assertContains(response, "path.startsWith('/catalog/compare')")
        self.assertContains(response, "!path.startsWith('/catalog/compare')")

    def test_opening_search_closes_mobile_menu(self):
        response = self.client.get("/")

        self.assertContains(
            response,
            'menuOpen = false; searchOpen = true; cartOpen = false; wishlistOpen = false; notifOpen = false;',
        )

    def test_mobile_navigation_is_not_hidden_by_scroll_script(self):
        response = self.client.get("/")
        html = response.content.decode("utf-8")

        behavior_start = html.index("MOBILE APP BEHAVIOR")
        behavior = html[behavior_start:]
        self.assertNotIn("classList.add('nav-hidden')", behavior)
        self.assertNotIn("classList.add('header-scroll-hide')", behavior)

    def test_mobile_header_is_fixed_and_search_has_rounded_offset_frame(self):
        css = (Path(settings.BASE_DIR) / "static/css/mobile_app.css").read_text(
            encoding="utf-8"
        )

        self.assertIn("overflow-x: clip !important", css)
        self.assertIn("FINAL MOBILE SHELL CONTRACT", css)
        self.assertIn("position: fixed !important", css)
        self.assertIn("padding-top: var(--mob-header-h) !important", css)
        self.assertIn("transform: none !important", css)
        self.assertIn(
            "--mob-safe-bottom: env(safe-area-inset-bottom, 0px)",
            css,
        )
        self.assertNotIn(
            "--mob-safe-bottom: max(10px, env(safe-area-inset-bottom, 0px))",
            css,
        )
        self.assertIn("--mob-nav-h: 52px", css)
        self.assertIn("justify-content: flex-end !important", css)
        self.assertIn("padding: 0 0 2px !important", css)
        self.assertIn("#header .header-search form select", css)
        self.assertIn("display: block !important", css)
        self.assertIn("border-radius: 16px !important", css)
        self.assertIn("top: 8px !important", css)

    def test_search_and_cart_have_backdrop_and_cart_drag_handle(self):
        response = self.client.get("/")
        css = (Path(settings.BASE_DIR) / "static/css/mobile_app.css").read_text(
            encoding="utf-8"
        )

        self.assertContains(response, 'class="mobile-shell-backdrop"')
        self.assertContains(response, "searchOpen || cartOpen")
        self.assertContains(response, 'class="mobile-mini-cart__handle"')
        self.assertContains(response, "cartDragOffset >= 72")
        self.assertContains(response, '@pointermove.window="cartDragMove($event)"')
        self.assertContains(response, "mobile-cart-open")
        self.assertContains(response, 'class="min-h-0 overflow-hidden"')
        self.assertNotContains(
            response,
            "z-[9999] overflow-y-auto max-h-[calc(100vh-80px)]",
        )
        self.assertIn(
            "bottom: 0 !important",
            css,
        )

    def test_cdek_header_count_is_shared_between_header_and_drawer(self):
        response = self.client.get("/")

        self.assertContains(response, "window.aspectLoadPvzCount")
        self.assertContains(response, "if (pending.has(key)) return pending.get(key)")
        self.assertContains(
            response,
            "const data = await window.aspectLoadPvzCount(this.city)",
        )

    def test_product_mobile_tabs_keep_natural_width_and_scroll(self):
        template = (
            Path(settings.BASE_DIR)
            / "apps/catalog/templates/catalog/detail.html"
        ).read_text(encoding="utf-8")

        self.assertIn("#product-tabs > div:first-child::-webkit-scrollbar", template)
        self.assertIn("overflow-x: auto !important", template)
        self.assertIn("flex: 0 0 auto !important", template)
        self.assertIn("min-width: max-content !important", template)
        self.assertIn("grid-template-columns: repeat(2, minmax(0, 1fr))", template)

    def test_mobile_compare_uses_desktop_sprite_icon(self):
        response = self.client.get("/")

        self.assertContains(response, "#icons--comparison")

    def test_catalog_does_not_render_obsolete_mobile_sort_button(self):
        response = self.client.get("/catalog/")

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'id="mobile-sort-btn"')
        self.assertContains(response, 'id="mobile-filter-btn"')

    def test_catalog_shows_mobile_reset_only_when_filters_are_active(self):
        unfiltered = self.client.get("/catalog/")
        filtered = self.client.get("/catalog/?acidity=medium")

        self.assertEqual(unfiltered.status_code, 200)
        self.assertEqual(filtered.status_code, 200)
        self.assertNotContains(unfiltered, 'data-testid="mobile-catalog-reset"')
        self.assertContains(filtered, 'data-testid="mobile-catalog-reset"')
        self.assertContains(filtered, "Сбросить фильтры")

    def test_non_coffee_sections_hide_coffee_only_mobile_controls(self):
        css = (Path(settings.BASE_DIR) / "static/css/mobile_app.css").read_text(
            encoding="utf-8"
        )

        self.assertIn(
            ".tc-catalog-page.non-coffee-section .tc-icon-btn",
            css,
        )
        self.assertIn(
            ".tc-catalog-page.non-coffee-section .tc-nav-tabs-list",
            css,
        )

    def test_non_coffee_desktop_grid_cannot_collapse_product_cards(self):
        template = (
            Path(settings.BASE_DIR)
            / "apps/catalog/templates/catalog/catalog.html"
        ).read_text(encoding="utf-8")

        self.assertIn(
            "#catalog-main.non-coffee-section .tc-catalog-layout",
            template,
        )
        self.assertIn(
            "grid-template-columns: minmax(0, 1fr) !important",
            template,
        )
        self.assertIn(
            "#catalog-main.non-coffee-section .tc-catalog-products",
            template,
        )
        self.assertIn(
            "#catalog-main.non-coffee-section .tc-product-grid",
            template,
        )
        self.assertIn("width: 100% !important", template)

    def test_open_mobile_menu_keeps_header_at_viewport_top(self):
        css = (Path(settings.BASE_DIR) / "static/css/mobile_app.css").read_text(
            encoding="utf-8"
        )

        final_contract = css[css.index("FINAL MOBILE SHELL CONTRACT") :]
        self.assertIn("#header.open-menu > div:first-child", final_contract)
        self.assertIn("height: 100dvh !important", final_contract)
        self.assertIn(
            "top: calc(var(--mob-header-h) + 8px) !important",
            final_contract,
        )

    def test_compare_action_uses_one_feedback_and_synchronizes_cards(self):
        js = (Path(settings.BASE_DIR) / "static/asset/js/custom.js").read_text(
            encoding="utf-8"
        )

        self.assertNotIn("showCompareBar", js)
        self.assertNotIn("compare-bar-inner", js)
        storage_index = js.index("localStorage.setItem('compare', JSON.stringify(list));")
        dispatch_index = js.index(
            "document.body.dispatchEvent(new CustomEvent('compareUpdated'",
            storage_index,
        )
        self.assertGreater(dispatch_index, storage_index)
