"""Загрузка лотов кофе из Excel в каталог.

Таблица «Информация о лотах»: строка заголовков, дальше по строке на лот.
Повторный запуск обновляет товар с тем же названием и не создаёт дубль.

Пример:
    python manage.py import_coffee --file "Информация о лотах1.xlsx"
"""
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.html import escape
from django.utils.text import slugify

from apps.catalog.models import (
    BrewMethod,
    Category,
    FlavorNote,
    GrindType,
    Product,
    ProductPackaging,
    ProductVariant,
    RoastType,
)

DEFAULT_PRICE = Decimal("1750.00")
DEFAULT_WEIGHT = 250
DEFAULT_STOCK = 50
DEFAULT_IMAGE = Path(__file__).resolve().parents[2] / "data" / "coffee-pack-250.jpg"

HEADER_FIELDS = (
    ("name", ("лот",)),
    ("country", ("страна",)),
    ("region", ("регион",)),
    ("roast_for", ("обжарено",)),
    ("processing", ("способ обработки", "обработк")),
    ("variety", ("разновидность",)),
    ("aroma", ("аромат",)),
    ("taste", ("вкус",)),
    ("altitude", ("высота",)),
    ("quality", ("классификатор", "качество")),
    ("screen", ("скрин", "размер зерна")),
    ("description", ("описание",)),
)


def clean(value):
    if value is None:
        return ""
    return str(value).replace("\xa0", " ").strip()


def clip(value, limit):
    text = clean(value)
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def header_map(row):
    found = {}
    for index, raw in enumerate(row):
        title = clean(raw).casefold()
        if not title:
            continue
        for field, needles in HEADER_FIELDS:
            if field in found:
                continue
            if any(needle in title for needle in needles):
                found[field] = index
                break
    if "name" not in found:
        return None
    return found


def row_dict(row, columns):
    data = {}
    for field, index in columns.items():
        data[field] = clean(row[index]) if index < len(row) else ""
    return data


def roast_kind(text):
    folded = clean(text).casefold().replace("ё", "е")
    has_filter = "фильтр" in folded
    has_espresso = "эспрессо" in folded or "espresso" in folded
    if "омни" in folded or (has_filter and has_espresso):
        return "omni"
    if has_espresso:
        return "espresso"
    if has_filter:
        return "filter"
    return ""


def q_score(text):
    match = re.search(r"Q\s*[—–\-]\s*(\d+(?:[.,]\d+)?)", clean(text), re.IGNORECASE)
    if not match:
        return ""
    return match.group(1).replace(",", ".")


def flavor_parts(text):
    parts = []
    seen = set()
    for chunk in re.split(r"[,;]", clean(text)):
        name = chunk.strip(" .")
        key = name.casefold()
        if not name or len(name) > 100 or key in seen:
            continue
        seen.add(key)
        parts.append(name)
    return parts


def unique_slug(model, value, max_length, exclude_pk=None):
    base = slugify(value, allow_unicode=True)[:max_length].strip("-") or "item"
    slug = base
    number = 2
    while True:
        taken = model.objects.filter(slug=slug)
        if exclude_pk:
            taken = taken.exclude(pk=exclude_pk)
        if not taken.exists():
            return slug
        suffix = f"-{number}"
        slug = f"{base[: max_length - len(suffix)]}{suffix}"
        number += 1


class Command(BaseCommand):
    help = "Импорт лотов кофе из Excel: категории по типу обжарки, товар, вкус и фасовка 250 г."

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            default="",
            help="Путь к xlsx. Если не указан, ищется «Информация о лотах1.xlsx» рядом с проектом.",
        )
        parser.add_argument(
            "--image",
            default="",
            help="Общая фотография для лотов без своего фото. По умолчанию пакет 250 г из каталога.",
        )
        parser.add_argument("--price", default=str(DEFAULT_PRICE), help="Цена новой фасовки 250 г.")
        parser.add_argument("--weight", type=int, default=DEFAULT_WEIGHT, help="Вес фасовки в граммах.")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Показать, что будет загружено, без записи в базу.",
        )

    def handle(self, *args, **options):
        path = self._find_workbook(options["file"])
        image_path = self._find_image(options["image"])
        try:
            price = Decimal(str(options["price"]).replace(",", "."))
        except InvalidOperation as exc:
            raise CommandError(f"Некорректная цена: {options['price']}") from exc
        if price <= 0:
            raise CommandError("Цена должна быть больше нуля.")
        weight = options["weight"]
        if weight <= 0:
            raise CommandError("Вес должен быть больше нуля.")

        try:
            from openpyxl import load_workbook
        except ImportError as exc:
            raise CommandError("Нужен пакет openpyxl.") from exc

        workbook = load_workbook(path, data_only=True, read_only=True)
        try:
            sheet = workbook.active
            rows = list(sheet.iter_rows(values_only=True))
        finally:
            workbook.close()

        columns = None
        start = 0
        for index, row in enumerate(rows):
            columns = header_map(row or ())
            if columns:
                start = index + 1
                break
        if not columns:
            raise CommandError("В первой строке не найдена колонка «Лот».")

        created = updated = skipped = 0
        for excel_row, row in enumerate(rows[start:], start=start + 1):
            data = row_dict(row or (), columns)
            if not data.get("name"):
                skipped += 1
                continue
            try:
                action = self._import_row(
                    data,
                    price=price,
                    weight=weight,
                    image_path=image_path,
                    dry_run=options["dry_run"],
                )
            except Exception as exc:
                skipped += 1
                self.stderr.write(f"Строка {excel_row}: {data.get('name')} — {exc}")
                continue
            if action == "created":
                created += 1
            else:
                updated += 1
            self.stdout.write(f"{action}: {data['name']}")

        self.stdout.write(self.style.SUCCESS(
            f"Готово. Создано: {created}, обновлено: {updated}, пропущено: {skipped}."
        ))

    def _find_workbook(self, raw):
        if raw:
            path = Path(raw)
            if not path.is_file():
                raise CommandError(f"Файл не найден: {path}")
            return path
        names = ("Информация о лотах1.xlsx",)
        roots = [Path.cwd(), Path.cwd().parent]
        try:
            from django.conf import settings
            roots.extend([Path(settings.BASE_DIR), Path(settings.BASE_DIR).parent])
        except Exception:
            pass
        for root in roots:
            for name in names:
                candidate = root / name
                if candidate.is_file():
                    return candidate
        raise CommandError(
            "Не найден файл «Информация о лотах1.xlsx». Укажите его: --file \"путь к файлу\"."
        )

    def _find_image(self, raw):
        if raw:
            path = Path(raw)
            if not path.is_file():
                raise CommandError(f"Картинка не найдена: {path}")
            return path
        if DEFAULT_IMAGE.is_file():
            return DEFAULT_IMAGE
        return None

    def _import_row(self, data, price, weight, image_path, dry_run):
        kind = roast_kind(data.get("roast_for"))
        score = q_score(data.get("quality"))
        if dry_run:
            exists = Product.objects.filter(name__iexact=data["name"]).exists()
            return "updated" if exists else "created"

        with transaction.atomic():
            product = Product.objects.filter(name__iexact=data["name"]).first()
            action = "updated" if product else "created"
            if product is None:
                product = Product(name=clip(data["name"], 300))
                product.slug = unique_slug(Product, product.name, 300)

            category = self._category(kind)
            description = self._description(data)
            product.name = clip(data["name"], 300)
            product.category = category
            product.origin_country = clip(data.get("country"), 100)
            product.region = clip(data.get("region"), 200)
            product.processing_method = clip(data.get("processing"), 100)
            product.variety = clip(data.get("variety"), 200)
            product.altitude = clip(data.get("altitude"), 100)
            product.q_score = clip(score, 32) or None
            product.short_description = clip(description, 500)
            product.description = description
            product.flavor_description_html = self._flavor_html(data)
            product.roast_level = {
                "espresso": Product.ROAST_ESPRESSO,
                "filter": Product.ROAST_MEDIUM,
                "omni": Product.ROAST_MEDIUM,
            }.get(kind, "")
            product.is_active = True
            product.in_stock = True
            product.is_microlot = "микролот" in description.casefold()
            product.save()

            notes = []
            for name in flavor_parts(data.get("taste")):
                notes.append(self._flavor(name))
            if notes:
                product.flavor_notes.set(notes)

            methods = self._brew_methods(kind)
            if methods:
                product.brew_methods.set(methods)

            self._ensure_offer(product, kind, price, weight)
            self._assign_image(product, image_path)
        return action

    def _category(self, kind):
        parent = (
            Category.objects.filter(slug__in=["kofe", "coffee"]).order_by("parent_id", "id").first()
            or Category.objects.filter(name__iexact="Кофе", parent__isnull=True).first()
        )
        if parent is None:
            parent = Category.objects.create(
                name="Кофе",
                slug="kofe",
                is_active=True,
                is_featured=True,
            )
        specs = {
            "filter": ("Кофе в зернах (Фильтр)", "kofe-filter", 10),
            "espresso": ("Кофе в зернах (Эспрессо)", "kofe-espresso", 20),
            "omni": ("Кофе в зернах (Фильтр и эспрессо)", "kofe-omni", 30),
        }
        name, slug, order = specs.get(kind, ("Кофе в зернах", "kofe-zerna", 40))
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
        if category.parent_id != parent.id:
            category.parent = parent
            category.save(update_fields=["parent"])
        return category

    def _description(self, data):
        parts = [clean(data.get("description"))]
        screen = clean(data.get("screen"))
        quality = clean(data.get("quality"))
        if screen:
            parts.append(f"Скрин / размер зерна: {screen}.")
        if quality:
            parts.append(f"Классификатор качества: {quality}.")
        return "\n\n".join(part for part in parts if part)

    def _flavor_html(self, data):
        blocks = []
        aroma = clean(data.get("aroma"))
        taste = clean(data.get("taste"))
        if aroma:
            blocks.append(f"<p><strong>Аромат:</strong> {escape(aroma)}</p>")
        if taste:
            blocks.append(f"<p><strong>Вкус:</strong> {escape(taste)}</p>")
        return "".join(blocks)

    def _flavor(self, name):
        note = FlavorNote.objects.filter(name__iexact=name).first()
        if note:
            return note
        return FlavorNote.objects.create(
            name=name,
            slug=unique_slug(FlavorNote, name, FlavorNote._meta.get_field("slug").max_length),
        )

    def _brew_methods(self, kind):
        wanted = {
            "filter": [("Фильтр", "filter")],
            "espresso": [("Эспрессо", "espresso")],
            "omni": [("Фильтр", "filter"), ("Эспрессо", "espresso")],
        }.get(kind, [])
        methods = []
        for name, slug in wanted:
            method = BrewMethod.objects.filter(slug=slug).first()
            if method is None:
                method, _created = BrewMethod.objects.get_or_create(slug=slug, defaults={"name": name})
            methods.append(method)
        return methods

    def _roast_type(self, kind):
        names = {
            "filter": ("Под фильтр", "pod-filtr"),
            "espresso": ("Под эспрессо", "pod-espresso"),
            "omni": ("Омни", "omni"),
        }
        name, slug = names.get(kind, ("Под фильтр", "pod-filtr"))
        roast, _created = RoastType.objects.get_or_create(
            slug=slug,
            defaults={"name": name, "is_active": True},
        )
        return roast

    def _ensure_offer(self, product, kind, price, weight):
        packaging = ProductPackaging.objects.filter(product=product, weight=weight).first()
        if packaging is None:
            packaging = ProductPackaging.objects.create(
                product=product,
                weight=weight,
                price=price,
                order=0,
                is_active=True,
            )
        grind, _created = GrindType.objects.get_or_create(
            slug="whole",
            defaults={"name": "В зёрнах", "is_active": True, "order": 0},
        )
        roast = self._roast_type(kind)
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
                stock_qty=DEFAULT_STOCK,
                sku=self._unique_sku(product.slug, weight, roast.slug),
            )

    def _unique_sku(self, product_slug, weight, roast_slug):
        base = slugify(f"{product_slug}-{weight}-{roast_slug}", allow_unicode=True) or "lot"
        sku = f"lot-{base}"[:100]
        number = 2
        while ProductVariant.objects.filter(sku=sku).exists():
            suffix = f"-{number}"
            sku = f"lot-{base}"[: 100 - len(suffix)] + suffix
            number += 1
        return sku

    def _assign_image(self, product, image_path):
        if image_path is None or product.main_image:
            return
        with image_path.open("rb") as handle:
            product.main_image.save(image_path.name, File(handle), save=True)
