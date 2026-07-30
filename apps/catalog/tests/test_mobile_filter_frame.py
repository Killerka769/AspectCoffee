from django.test import TestCase


class MobileFilterFrameTests(TestCase):
    def test_filter_frame_scrolls_only_its_content(self):
        response = self.client.get("/catalog/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, ".tc-sidebar.is-open .tc-sidebar__inner")
        self.assertContains(response, "overflow-y: auto")
        self.assertContains(response, "overscroll-behavior-y: contain")
        self.assertContains(response, "body.tc-filter-scroll-lock")
        self.assertNotContains(response, "padding: 80px 20px 100px")

    def test_filter_frame_has_mobile_header_and_close_controls(self):
        response = self.client.get("/catalog/")

        self.assertContains(response, 'class="tc-filter-mobile-header"')
        self.assertContains(response, 'id="mobile-filter-close"')
        self.assertContains(response, "top: 76px")
        self.assertContains(response, "bottom: 64px")
        self.assertContains(response, "height: calc(100dvh - 140px)")
        self.assertContains(response, "max-height: calc(100dvh - 140px)")
        self.assertContains(response, "#catalog-main.tc-filter-host-open")
        self.assertContains(response, ".tc-container > :not(.tc-catalog-layout)")
        self.assertContains(response, ".tc-catalog-products")
        self.assertContains(response, "visibility: hidden !important")
        self.assertContains(response, "window.tcMobileFiltersBound")

    def test_mobile_sorting_uses_scrollable_chips_without_duplicate_icon(self):
        response = self.client.get("/catalog/")

        self.assertNotContains(response, 'id="mobile-sort-btn"')
        self.assertContains(response, "Популярные")
        self.assertContains(response, "Сначала новые")
        self.assertContains(response, "С высоким рейтингом")
        self.assertContains(response, "Сначала дешевле")
        self.assertContains(response, "Сначала дороже")
        self.assertContains(response, ".tc-mobile-sort-only { display: block; }")
        self.assertContains(response, ".tc-nav-tabs-sort { display: none !important; }")
        self.assertContains(response, "box-shadow: inset 0 0 0 1px rgba(0,0,0,0.12)")

    def test_active_filters_show_reset_and_controls_bind_immediately(self):
        response = self.client.get("/catalog/?sort=variants__price")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="tc-filter-mobile-reset"')
        self.assertContains(response, "Сбросить фильтры")
        self.assertContains(response, "(function initCatalogMobileUi()")
        self.assertContains(response, 'aria-controls="sidebar-filters"')
        self.assertContains(response, "trigger.setAttribute('aria-expanded', 'true')")
