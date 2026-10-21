from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, override_settings

from apps.delivery.cdek import CDEKClient


class CDEKConfigurationTests(SimpleTestCase):
    @override_settings(CDEK_TEST_MODE=False, CDEK_API_URL="")
    def test_live_mode_selects_live_api(self):
        self.assertEqual(CDEKClient().base_url, "https://api.cdek.ru/v2")

    @override_settings(CDEK_TEST_MODE=True, CDEK_API_URL="")
    def test_test_mode_selects_sandbox_without_code_changes(self):
        self.assertEqual(CDEKClient().base_url, "https://api.edu.cdek.ru/v2")

    @override_settings(CDEK_TEST_MODE=True, CDEK_API_URL="https://api.cdek.ru/v2")
    def test_test_mode_cannot_accidentally_use_live_api(self):
        with self.assertRaises(ImproperlyConfigured):
            CDEKClient()

    @override_settings(CDEK_TEST_MODE=False, CDEK_API_URL="https://api.edu.cdek.ru/v2")
    def test_sandbox_endpoint_cannot_be_reported_as_live(self):
        with self.assertRaises(ImproperlyConfigured):
            CDEKClient()

    def test_unsafe_endpoint_is_rejected_before_network(self):
        for url in ("http://api.cdek.ru/v2", "https://user:secret@api.cdek.ru/v2", "https://api.cdek.ru/v2?token=secret"):
            with self.subTest(url=url), override_settings(CDEK_API_URL=url):
                with self.assertRaises(ImproperlyConfigured):
                    CDEKClient()
