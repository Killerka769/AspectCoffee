"""Демо-наполнение фасовок и комбинаций помол×обжарка (ТЗ 1.7).

Для нескольких показательных кофейных товаров создаёт:
- 4 фасовки (250/500/750/1000 г) с разными ценами (цена — только от фасовки, 1.7.1);
- 9 комбинаций помол×обжарка (3 помола × 3 обжарки) на каждую фасовку (1.7.4);
- для зёрен — обжарку «Без обжарки» (зелёный, 1.7.2).
"""
from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.catalog.models import (
    Product, ProductPackaging, ProductVariant, GrindType, RoastType,
)

WEIGHT_PRICE = [(250, 1000), (500, 1500), (750, 2000), (1000, 2500)]
GRIND_SLUGS = ["whole", "fine", "medium"]
ROAST_SLUGS = ["light", "medium", "dark"]


class Command(BaseCommand):
    help = "1.7 — засеять демо-фасовки и комбинации помол×обжарка для нескольких товаров."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=6, help="Сколько товаров наполнить")

    def handle(self, *args, **opts):
        limit = opts["limit"]
        grinds = {g.slug: g for g in GrindType.objects.all()}
        roasts = {r.slug: r for r in RoastType.objects.all()}
        green = roasts.get("green")

        # Берём кофейные товары (раздел «Кофе» или его дочерние).
        products = list(
            Product.objects.filter(is_active=True)
            .filter(category__slug__in=["kofe", "coffee"])
            .order_by("id")[:limit]
        )
        if len(products) < limit:
            extra = (
                Product.objects.filter(is_active=True)
                .exclude(id__in=[p.id for p in products])
                .order_by("id")[: limit - len(products)]
            )
            products += list(extra)

        for product in products:
            # Чистим старые варианты/фасовки, чтобы пересоздать матрицу.
            ProductVariant.objects.filter(product=product).delete()
            ProductPackaging.objects.filter(product=product).delete()

            for order, (weight, price) in enumerate(WEIGHT_PRICE):
                pkg = ProductPackaging.objects.create(
                    product=product, weight=weight,
                    price=Decimal(price), order=order,
                )
                for g_slug in GRIND_SLUGS:
                    for r_slug in ROAST_SLUGS:
                        ProductVariant.objects.create(
                            product=product, packaging=pkg,
                            grind_type=grinds[g_slug], roast_type=roasts[r_slug],
                            stock_qty=25,
                            sku=f"{product.slug}-{weight}-{g_slug}-{r_slug}",
                        )
                # «Зелёный» (без обжарки) только для зёрен (1.7.2).
                if green is not None:
                    ProductVariant.objects.create(
                        product=product, packaging=pkg,
                        grind_type=grinds["whole"], roast_type=green,
                        stock_qty=10,
                        sku=f"{product.slug}-{weight}-whole-green",
                    )

            cnt = ProductVariant.objects.filter(product=product).count()
            self.stdout.write(
                f"{product.slug:40} фасовок=4, комбинаций/вариантов={cnt}"
            )

        self.stdout.write(self.style.SUCCESS(f"Готово: наполнено товаров={len(products)}"))
