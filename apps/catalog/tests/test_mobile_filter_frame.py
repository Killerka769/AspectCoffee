from django.test import TestCase


class MobileFilterFrameTests(TestCase):
    def test_filter_frame_scroll_is_isolated_from_document(self):
        response = self.client.get("/catalog/")
        self.assertEqual(response.status_code, 200)
        for value in ("aspect-sidebar", "overflow-y: auto", "overscroll-behavior-y:contain", "tc-filter-scroll-lock"):
            self.assertContains(response, value)

    def test_filter_has_accessible_open_close_and_escape_controls(self):
        response = self.client.get("/catalog/")
        for value in ('aria-controls="sidebar-filters"', 'id="mobile-filter-close"', "addEventListener('click', closeSidebar)", "e.key === 'Escape'", "setAttribute('aria-expanded','true')"):
            self.assertContains(response, value)

    def test_current_sort_options_remain_available(self):
        response = self.client.get("/catalog/")
        for label in ("Популярные", "Сначала новые", "С высоким рейтингом", "Сначала дешевле", "Сначала дороже"):
            self.assertContains(response, label)
        self.assertNotContains(response, 'id="mobile-sort-btn"')

    def test_reset_is_only_offered_when_query_is_active(self):
        self.assertNotContains(self.client.get("/catalog/"), 'data-testid="mobile-catalog-reset"')
        response = self.client.get("/catalog/?sort=variants__price")
        self.assertContains(response, 'data-testid="mobile-catalog-reset"')
        self.assertContains(response, 'href="/catalog/"')
