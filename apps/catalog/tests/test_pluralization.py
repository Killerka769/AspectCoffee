from django.test import SimpleTestCase

from apps.catalog.templatetags.catalog_extras import ru_plural


class RussianPluralizationTests(SimpleTestCase):
    def test_sort_forms(self):
        cases = {
            1: "сорт",
            3: "сорта",
            11: "сортов",
            12: "сортов",
            14: "сортов",
            21: "сорт",
            321: "сорт",
        }
        for value, expected in cases.items():
            with self.subTest(value=value):
                self.assertEqual(ru_plural(value, "сорт,сорта,сортов"), expected)

    def test_order_forms(self):
        cases = {
            1: "заказ",
            2: "заказа",
            5: "заказов",
            11: "заказов",
            14: "заказов",
            21: "заказ",
            22: "заказа",
            25: "заказов",
        }
        for value, expected in cases.items():
            with self.subTest(value=value):
                self.assertEqual(ru_plural(value, "заказ,заказа,заказов"), expected)
