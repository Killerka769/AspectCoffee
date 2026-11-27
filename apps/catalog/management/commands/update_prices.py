"""Розничные цены и разделы из прайс-листа Aspect Coffee от 25.09.2026.

Цены вписаны из PDF, без разбора файла при запуске. Совпадение с товаром —
по вхождению названия. Повторный запуск обновляет те же фасовки.

    python manage.py update_prices
    python manage.py update_prices --dry-run
"""
import re
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from apps.catalog.models import (
    Category,
    GrindType,
    Product,
    ProductPackaging,
    ProductVariant,
    RoastType,
)

PLACEHOLDER_250 = Decimal("1750.00")

# section, название в прайсе, розница 250 г или None, розница 1 кг, алиасы для поиска
LOTS = (
    ("commercial", "Уганда Другар", None, None, ("уганда другар",)),
    ("milk", "Бразилия Мока PB", None, Decimal("2500.00"), ("бразилия мока",)),
    ("milk", "Бразилия Жёлтый Бурбон PB", None, Decimal("2600.00"), ("бразилия желтый бурбон", "бразилия жёлтый бурбон")),
    ("espresso", "Бразилия Даниил Барбоса", None, Decimal("4500.00"), ("бразилия даниил барбоса",)),
    ("espresso", "Гватемала ла Делисия", None, Decimal("3300.00"), ("гватемала ла делисия",)),
    ("espresso", "Руанда Нгома Ньямагабе", None, Decimal("3600.00"), ("руанда нгома",)),
    ("espresso", "Д.Р. Конго Нямасаса Калехе", None, Decimal("3800.00"), ("конго нямасаса", "калехе")),
    ("espresso", "Индонезия Суматра Киринчи", None, Decimal("4400.00"), ("суматра керинчи", "суматра киринчи")),
    ("espresso", "Колумбия Агустин эль Осо", None, Decimal("3600.00"), ("агустин эль осо", "агустин")),
    ("espresso", "Колумбия Апонте", None, Decimal("4400.00"), ("колумбия апонте", "апонте")),
    ("espresso", "Колумбия эль Индио", None, Decimal("4400.00"), ("эль индио", "эль индио")),
    ("espresso", "Эфиопия Гуджи Мар-Коф", None, Decimal("3000.00"), ("гуджи мар-коф", "гуджи мар коф")),
    ("espresso", "Эфиопия Сидамо Ардент", None, Decimal("4500.00"), ("сидамо ардент",)),
    ("espresso", "Эфиопия Бенч-Маджи Гейша", None, Decimal("5800.00"), ("бенч-маджи", "бенч маджи")),
    ("filter", "Колумбия Агустин эль Осо", Decimal("900.00"), Decimal("3600.00"), ("агустин эль осо", "агустин")),
    ("filter", "Колумбия Апонте", Decimal("1100.00"), Decimal("4400.00"), ("колумбия апонте", "апонте")),
    ("filter", "Колумбия эль Индио", Decimal("1100.00"), Decimal("4400.00"), ("эль индио",)),
    ("filter", "Колумбия Вергель Элиас", Decimal("1450.00"), Decimal("5800.00"), ("вергель элиас",)),
    ("filter", "Колумбия Вергель Шади", Decimal("1350.00"), Decimal("5400.00"), ("вергель шади",)),
    ("filter", "Д.Р. Конго Нямасаса Калехе", Decimal("950.00"), Decimal("3800.00"), ("конго нямасаса", "калехе")),
    ("filter", "Эфиопия Гуджи Мар-Коф", Decimal("750.00"), Decimal("3000.00"), ("гуджи мар-коф", "гуджи мар коф")),
    ("filter", "Эфиопия Сидамо Ардент", Decimal("1125.00"), Decimal("4500.00"), ("сидамо ардент",)),
    ("filter", "Эфиопия Гелана Абая Гейша", Decimal("1450.00"), Decimal("5800.00"), ("гелана абая", "гелана")),
    ("filter", "Кения Кабингара Кириньяга", Decimal("1100.00"), Decimal("4400.00"), ("кабингара",)),
    ("filter", "Кения Киангундо Киама", Decimal("1125.00"), Decimal("4500.00"), ("киангундо",)),
    ("decaf", "Гватемала Декаф", None, Decimal("3500.00"), ("гватемала декаф", "декаф")),
)

SECTIONS = (
    ("commercial", "Коммерческий кофе", "kofe-commercial", 10),
    ("milk", "Кофе под молочные напитки", "kofe-milk", 20),
    ("espresso", "Кофе под эспрессо", "kofe-espresso", 30),
    ("filter", "Кофе под фильтр", "kofe-filter", 40),
    ("decaf", "Кофе без кофеина", "kofe-decaf", 50),
)

ROAST_BY_SECTION = {
    "espresso": ("Под эспрессо", "pod-espresso"),
    "filter": ("Под фильтр", "pod-filtr"),
    "milk": ("Под эспрессо", "pod-espresso"),
    "decaf": ("Омни", "omni"),
    "commercial": ("Под эспрессо", "pod-espresso"),
}


def normalize(value):
    text = (value or "").casefold().replace("ё", "е")
    text = text.replace("киринчи", "керинчи")
    text = re.sub(r"[^a-zа-я0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def section_hint(name):
    folded = normalize(name)
    if "декаф" in folded or "без кофеина" in folded:
        return "decaf"
    if "эспрессо" in folded:
        return "espresso"
    if "фильтр" in folded:
        return "filter"
    return None


def find_lot(product_name):
    folded = normalize(product_name)
    hint = section_hint(product_name)
    scored = []
    for lot in LOTS:
        section, title, price_250, price_1000, aliases = lot
        best = 0
        for alias in aliases:
            needle = normalize(alias)
            if needle and needle in folded:
                best = max(best, len(needle))
        if best:
            scored.append((best, lot))
    if hint:
        preferred = [item for item in scored if item[1][0] == hint]
        if preferred:
            scored = preferred
    if not scored:
        return None
    scored.sort(key=lambda item: item[0], reverse=True)
    top = scored[0][0]
    winners = []
    for length, lot in scored:
        if length != top:
            break
        if lot not in winners:
            winners.append(lot)
    if len(winners) != 1:
        return None
    section, title, price_250, price_1000, aliases = winners[0]
    return {
        "section": section,
        "title": title,
        "price_250": price_250,
        "price_1000": price_1000,
    }


class Command(BaseCommand):
    help = "Поставить розничные цены 250 г и 1 кг из прайса и разложить лоты по его разделам."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Только показать изменения.")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        categories = self._categories(dry_run)
        matched_titles = set()
        updated = skipped = 0
        products = Product.objects.select_related("category").order_by("name")
        for product in products:
            lot = find_lot(product.name)
            if lot is None:
                continue
            matched_titles.add((lot["section"], lot["title"]))
            self.stdout.write(f"{product.name} → {lot['title']} / {categories[lot['section']].name}")
            if dry_run:
                self._report_prices(lot)
                updated += 1
                continue
            with transaction.atomic():
                self._assign_category(product, categories[lot["section"]])
                self._apply_prices(product, lot)
            updated += 1
        for lot in LOTS:
            key = (lot[0], lot[1])
            if key not in matched_titles and (lot[2] is not None or lot[3] is not None or lot[0] == "commercial"):
                skipped += 1
                self.stdout.write(self.style.WARNING(f"В базе нет: {lot[1]} ({lot[0]})"))
        if not dry_run:
            self._retire_old_brew_category()
        self.stdout.write(self.style.SUCCESS(f"Готово. Обновлено товаров: {updated}, в базе нет строк прайса: {skipped}."))

    def _report_prices(self, lot):
        if lot["price_250"] is not None:
            self.stdout.write(f"  250 г = {lot['price_250']} ₽")
        else:
            self.stdout.write("  250 г в прайсе нет")
        if lot["price_1000"] is not None:
            self.stdout.write(f"  1 кг = {lot['price_1000']} ₽")

    def _categories(self, dry_run):
        parent = (
            Category.objects.filter(slug__in=["kofe", "coffee"]).order_by("id").first()
            or Category.objects.filter(name__iexact="Кофе", parent__isnull=True).first()
        )
        if parent is None and not dry_run:
            parent = Category.objects.create(name="Кофе", slug="kofe", is_active=True, is_featured=True)
        result = {}
        for key, name, slug, order in SECTIONS:
            if dry_run:
                category = Category.objects.filter(slug=slug).first() or Category(name=name, slug=slug)
                result[key] = category
                continue
            category, _created = Category.objects.get_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "parent": parent,
                    "is_active": True,
                    "is_featured": False,
                    "order": order,
                },
            )
            category.name = name
            category.parent = parent
            category.is_active = True
            category.is_featured = False
            category.order = order
            category.save()
            result[key] = category
        return result

    def _assign_category(self, product, category):
        if product.category_id != category.id:
            product.category = category
            product.save(update_fields=["category"])

    def _apply_prices(self, product, lot):
        if lot["price_250"] is not None:
            self._set_price(product, 250, lot["price_250"], lot["section"], order=0)
        else:
            self._drop_placeholder_250(product)
        if lot["price_1000"] is not None:
            self._set_price(product, 1000, lot["price_1000"], lot["section"], order=1)

    def _drop_placeholder_250(self, product):
        packaging = ProductPackaging.objects.filter(product=product, weight=250).first()
        if packaging is None:
            self.stdout.write("  250 г в прайсе нет")
            return
        if packaging.price != PLACEHOLDER_250:
            self.stdout.write(f"  250 г в прайсе нет, оставлена цена {packaging.price} ₽")
            return
        packaging.variants.all().delete()
        packaging.delete()
        self.stdout.write("  заглушка 250 г / 1750 ₽ убрана: в прайсе этой фасовки нет")

    def _set_price(self, product, weight, price, section, order):
        packaging = ProductPackaging.objects.filter(product=product, weight=weight).first()
        if packaging is None:
            packaging = ProductPackaging.objects.create(
                product=product,
                weight=weight,
                price=price,
                order=order,
                is_active=True,
            )
            self.stdout.write(f"  {weight} г: создана, {price} ₽")
        else:
            previous = packaging.price
            packaging.price = price
            packaging.old_price = None
            packaging.is_active = True
            packaging.order = order
            packaging.save(update_fields=["price", "old_price", "is_active", "order"])
            self.stdout.write(f"  {weight} г: {previous} → {price} ₽")
        self._ensure_variant(product, packaging, section)

    def _ensure_variant(self, product, packaging, section):
        existing = product.variants.filter(packaging=packaging).first() or product.variants.first()
        grind = existing.grind_type if existing and existing.grind_type_id else self._whole_bean()
        roast = existing.roast_type if existing and existing.roast_type_id else self._roast(section)
        variant = ProductVariant.objects.filter(
            product=product,
            packaging=packaging,
            grind_type=grind,
            roast_type=roast,
        ).first()
        if variant is None:
            ProductVariant.objects.create(
                product=product,
                packaging=packaging,
                grind_type=grind,
                roast_type=roast,
                stock_qty=50,
                sku=self._sku(product, packaging.weight, roast.slug if roast else "bean"),
            )
            return
        variant.save()

    def _whole_bean(self):
        grind, _created = GrindType.objects.get_or_create(
            slug="whole",
            defaults={"name": "В зёрнах", "is_active": True, "order": 0},
        )
        return grind

    def _roast(self, section):
        name, slug = ROAST_BY_SECTION.get(section, ("Под фильтр", "pod-filtr"))
        roast, _created = RoastType.objects.get_or_create(
            slug=slug,
            defaults={"name": name, "is_active": True},
        )
        return roast

    def _sku(self, product, weight, roast_slug):
        base = slugify(f"{product.slug}-{weight}-{roast_slug}") or f"lot-{product.pk}"
        sku = f"lot-{base}"[:100]
        number = 2
        while ProductVariant.objects.filter(sku=sku).exists():
            suffix = f"-{number}"
            sku = f"lot-{base}"[: 100 - len(suffix)] + suffix
            number += 1
        return sku

    def _retire_old_brew_category(self):
        old = Category.objects.filter(slug="kofe-omni").first()
        if old and not old.products.exists():
            old.is_active = False
            old.save(update_fields=["is_active"])
