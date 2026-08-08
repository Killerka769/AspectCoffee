from decimal import Decimal

from django.template.loader import render_to_string
from django.test import TestCase

from apps.catalog.models import (
    Category,
    GrindType,
    Product,
    ProductPackaging,
    ProductVariant,
    RoastType,
)


class OptionalProductAttributesTests(TestCase):
    def test_noncoffee_product_without_optional_data_renders_price_only(self):
        category = Category.objects.create(name="Аксессуары", slug="aksessuary")
        product = Product.objects.create(
            name="Чехол",
            slug="chehol",
            category=category,
            short_description="Треугольный чехол",
        )
        packaging = ProductPackaging.objects.create(
            product=product,
            weight=None,
            price=Decimal("1899.00"),
        )
        ProductVariant.objects.create(
            product=product,
            packaging=packaging,
            stock_qty=3,
        )

        html = render_to_string("catalog/_product_card.html", {"product": product})

        self.assertIn("1899", html)
        self.assertNotIn("для фильтра", html)
        self.assertNotIn("мытый", html)
        self.assertNotIn("Плотность", html)
        self.assertNotIn("Кислотность", html)
        self.assertNotIn("в зёрнах", html)
        self.assertNotIn("250 г", html)

    def test_coffee_product_keeps_filled_coffee_options(self):
        root = Category.objects.create(name="Кофе", slug="kofe")
        category = Category.objects.create(
            name="Для эспрессо",
            slug="espresso",
            parent=root,
        )
        product = Product.objects.create(
            name="Уганда",
            slug="uganda",
            category=category,
            roast_level=Product.ROAST_ESPRESSO,
            processing_method="мытый",
            body=6,
            acidity=4,
        )
        packaging = ProductPackaging.objects.create(
            product=product,
            weight=250,
            price=Decimal("627.00"),
        )
        grind, _ = GrindType.objects.get_or_create(
            slug="whole", defaults={"name": "В зёрнах"},
        )
        roast, _ = RoastType.objects.get_or_create(
            slug="medium", defaults={"name": "Средняя"},
        )
        ProductVariant.objects.create(
            product=product,
            packaging=packaging,
            grind_type=grind,
            roast_type=roast,
            stock_qty=3,
        )

        html = render_to_string("catalog/_product_card.html", {"product": product})

        self.assertTrue(product.is_coffee_product)
        self.assertIn("для эспрессо", html)
        self.assertIn("мытый", html)
        self.assertIn("Плотность", html)
        self.assertIn("Кислотность", html)
        self.assertIn("250 г", html)
        self.assertIn("В зёрнах", html)
