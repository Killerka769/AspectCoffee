from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse


class CDEKPvzCountTests(TestCase):
    def setUp(self):
        cache.clear()

    @patch("apps.delivery.views.CDEKClient")
    def test_returns_total_count_for_russia(self, client_class):
        cdek = client_class.return_value
        cdek.configured.return_value = True
        cdek.get_office_count.return_value = 9878

        response = self.client.get(reverse("delivery:cdek_pvz_count"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "city": "Россия",
            "city_code": None,
            "count": 9878,
        })
        cdek.get_office_count.assert_called_once_with(city_code=None, country_code="RU")

    @patch("apps.delivery.views.CDEKClient")
    def test_returns_count_for_selected_city(self, client_class):
        cdek = client_class.return_value
        cdek.configured.return_value = True
        cdek.search_cities.return_value = [{
            "code": 44,
            "city": "Москва",
            "region": "Москва",
            "country": "Россия",
        }]
        cdek.get_office_count.return_value = 491

        response = self.client.get(
            reverse("delivery:cdek_pvz_count"),
            {"city": "Москва"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "city": "Москва",
            "city_code": 44,
            "count": 491,
        })
        cdek.get_office_count.assert_called_once_with(city_code=44, country_code="RU")

    @patch("apps.delivery.views.CDEKClient")
    def test_hides_feature_when_cdek_is_unavailable(self, client_class):
        cdek = client_class.return_value
        cdek.configured.return_value = True
        cdek.get_office_count.return_value = None

        response = self.client.get(reverse("delivery:cdek_pvz_count"))

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["error"], "СДЭК временно недоступен")

    def test_rejects_city_outside_header_list(self):
        response = self.client.get(
            reverse("delivery:cdek_pvz_count"),
            {"city": "Неизвестный город"},
        )

        self.assertEqual(response.status_code, 400)
