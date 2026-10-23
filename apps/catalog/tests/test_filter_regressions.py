from django.test import TestCase

from apps.blog.models import BlogPost
from apps.catalog.facets import build_facets
from apps.catalog.models import Product


class CatalogFilterRegressionTests(TestCase):
    def setUp(self):
        pass

    def test_processing_facet_count_matches_case_insensitive_filter(self):
        Product.objects.create(
            name="Смесь с заглавной буквы",
            slug="blend-upper",
            processing_method="Смесь",
            is_active=True,
        )
        Product.objects.create(
            name="Смесь со строчной буквы",
            slug="blend-lower",
            processing_method="смесь",
            is_active=True,
        )

        facets, _ = build_facets(Product.objects.filter(is_active=True))
        blend_options = [
            option for option in facets["processing"]
            if option["name"].casefold() == "смесь"
        ]

        self.assertEqual(len(blend_options), 1)
        self.assertEqual(blend_options[0]["count"], 2)

        response = self.client.get("/catalog/", {"processing": blend_options[0]["value"]})
        self.assertContains(response, "2 сорта из 2")

    def test_processing_value_with_comma_is_not_split(self):
        value = "без кофеина, этилацетат"
        Product.objects.create(
            name="Декаф",
            slug="decaf",
            processing_method=value,
            is_active=True,
        )
        Product.objects.create(
            name="Обычный кофе",
            slug="regular",
            processing_method="мытый",
            is_active=True,
        )

        response = self.client.get("/catalog/", {"processing": value})

        self.assertContains(response, "1 сорт из 2")

    def test_retired_recipe_detail_is_not_exposed(self):
        self.assertEqual(self.client.get("/recipes/retired-recipe/").status_code, 404)

    def test_search_suggestions_respect_selected_scope(self):
        Product.objects.create(
            name="Чай Ассам",
            slug="assam-tea",
            short_description="Каталожный чай",
            is_active=True,
        )
        BlogPost.objects.create(
            title="Как правильно заваривать чай",
            slug="brew-tea",
            short_description="Статья про чай",
            content="Подробная инструкция",
            is_published=True,
        )

        catalog_response = self.client.get(
            "/search/suggest/", {"q": "чай", "scope": "catalog"}
        )
        blog_response = self.client.get(
            "/search/suggest/", {"q": "чай", "scope": "blog"}
        )

        self.assertTrue(catalog_response.json()["products"])
        self.assertEqual(catalog_response.json()["posts"], [])
        self.assertEqual(blog_response.json()["products"], [])
        self.assertTrue(blog_response.json()["posts"])

    def test_blog_search_page_filters_by_query(self):
        matching = BlogPost.objects.create(
            title="Чай в кулинарии",
            slug="tea-in-cooking",
            content="Материал о чае",
            is_published=True,
        )
        other = BlogPost.objects.create(
            title="Обжарка кофе",
            slug="coffee-roasting",
            content="Материал о кофе",
            is_published=True,
        )

        response = self.client.get("/blog/", {"q": "чай"})

        self.assertContains(response, matching.title)
        self.assertNotContains(response, other.title)
        self.assertEqual(response.context["search_query"], "чай")
