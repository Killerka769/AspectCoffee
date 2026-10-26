
from decimal import Decimal, ROUND_HALF_UP
from django.db import models
from django.utils.text import slugify
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings
from imagekit.models import ProcessedImageField
from imagekit.processors import ResizeToFit, ResizeToFill
from ckeditor_uploader.fields import RichTextUploadingField

# class Roaster(models.Model):
#     name = models.CharField("Название", max_length=200, unique=True)
#     slug = models.SlugField("Адрес в URL", max_length=200, unique=True, blank=True)
#     description = models.TextField("Описание", blank=True)
#     image = models.ImageField("Фото", upload_to="roasters/", blank=True)
#     is_active = models.BooleanField("Активен", default=True)

#     class Meta:
#         verbose_name = "Ростер"
#         verbose_name_plural = "Ростеры"
#         ordering = ["name"]

#     def __str__(self):
#         return self.name

#     def get_absolute_url(self):
#         from django.urls import reverse
#         return reverse("catalog:recipe_detail", kwargs={"slug": self.slug})

#     def save(self, *args, **kwargs):
#         if not self.slug:
#             self.slug = slugify(self.name)
#         super().save(*args, **kwargs)


class Category(models.Model):
    name = models.CharField("Название", max_length=200)
    slug = models.SlugField("Адрес в URL", max_length=200, unique=True)
    parent = models.ForeignKey(
        "self", null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="children",
        verbose_name="Родительская категория",
    )
    description = models.TextField("Описание", blank=True)
    image = ProcessedImageField(
        upload_to="categories/",
        processors=[ResizeToFit(800, 400)],
        format="WEBP",
        options={"quality": 85},
        blank=True, null=True,
        verbose_name="Изображение",
    )
    seo_title = models.CharField("SEO Title", max_length=255, blank=True)
    seo_description = models.TextField("SEO Description", blank=True)
    h1 = models.CharField("H1", max_length=255, blank=True)
    is_active = models.BooleanField("Активна", default=True)
    is_featured = models.BooleanField(
        "В основной строке хэштегов",
        default=True,
        help_text="Если включено — показывать в основной строке, иначе в скрытой (при нажатии ∨)",
    )
    order = models.PositiveIntegerField("Порядок", default=0, db_index=True)
    created_at = models.DateTimeField("Создана", auto_now_add=True)
    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
        ordering = ["order", "name"]
        indexes = [models.Index(fields=["slug"])]
    def __str__(self):
        return self.name
    # Обратные алиасы slug для ЧПУ (реальный slug в БД -> англ. в URL).
    SECTION_URL_ALIASES = {
        "kofe": "coffee",
        "chay": "tea",
        "aksessuary": "accessories",
    }

    def get_absolute_url(self):
        # 1.4.7 — ЧПУ по иерархии: раздел /<section>/, категория /<section>/<child>/.
        def url_slug(slug):
            return self.SECTION_URL_ALIASES.get(slug, slug)
        if self.parent_id and self.parent:
            return f"/{url_slug(self.parent.slug)}/{self.slug}/"
        return f"/{url_slug(self.slug)}/"
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)
# class Tag(models.Model):
#     name = models.CharField("Название", max_length=100, unique=True)
#     slug = models.SlugField("Адрес в URL", unique=True)
#     class Meta:
#         verbose_name = "Тег"
#         verbose_name_plural = "Теги"
#     def __str__(self):
#         return self.name
class FlavorNote(models.Model):
    name = models.CharField("Вкусовая нотка", max_length=100, unique=True)
    slug = models.SlugField("Адрес в URL", unique=True)
    class Meta:
        verbose_name = "Вкусовая нотка"
        verbose_name_plural = "Вкусовые нотки"
    def __str__(self):
        return self.name
class BrewMethod(models.Model):
    name = models.CharField("Способ приготовления", max_length=100, unique=True)
    slug = models.SlugField("Адрес в URL", unique=True)
    guide_url = models.CharField("URL руководства", max_length=500, blank=True, help_text="Например: /blog/guide-espresso")
    class Meta:
        verbose_name = "Способ приготовления"
        verbose_name_plural = "Способы приготовления"
    def __str__(self):
        return self.name
class Product(models.Model):
    ROAST_LIGHT = "light"
    ROAST_MEDIUM = "medium"
    ROAST_DARK = "dark"
    ROAST_ESPRESSO = "espresso"
    ROAST_CHOICES = [
        (ROAST_LIGHT, "Светлая"),
        (ROAST_MEDIUM, "Средняя"),
        (ROAST_DARK, "Тёмная"),
        (ROAST_ESPRESSO, "Эспрессо"),
    ]
    name = models.CharField("Название", max_length=300)
    slug = models.SlugField("Адрес в URL", max_length=300, unique=True, db_index=True)
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL,
        null=True, related_name="products",
        verbose_name="Категория",
    )
    description = RichTextUploadingField("Описание", blank=True)
    storage_description = RichTextUploadingField("Хранение", blank=True)
    delivery_description = RichTextUploadingField("Доставка", blank=True)
    short_description = models.TextField("Краткое описание", blank=True, max_length=500)
    roast_level = models.CharField(
        "Степень обжарки",
        max_length=32,
        blank=True,
        choices=ROAST_CHOICES,
    )
    processing_method = models.CharField("Метод обработки", max_length=100, blank=True)
    origin_country = models.CharField("Страна происхождения", max_length=100, blank=True)
    composition = models.TextField("Состав", blank=True)
    altitude = models.CharField("Высота произрастания", max_length=100, blank=True)
    region = models.CharField("Регион", max_length=200, blank=True)
    q_score = models.CharField("Оценка Q-грейдера", max_length=32, null=True, blank=True)
    harvest_year = models.CharField("Урожай", max_length=20, blank=True)
    variety = models.CharField("Разновидность", max_length=200, blank=True)
    caffeine_content = models.DecimalField("Содержание кофеина (%)", max_digits=4, decimal_places=2, null=True, blank=True)
    # roaster_machine = models.CharField("Ростер для обжарки", max_length=100, blank=True)
    # roaster = models.ForeignKey(Roaster, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Ростер")
    body = models.PositiveIntegerField(
        "Плотность (Тельце)", null=True, blank=True, default=None,
        validators=[MinValueValidator(0), MaxValueValidator(10)]
    )
    acidity = models.PositiveIntegerField(
        "Кислотность", null=True, blank=True, default=None,
        validators=[MinValueValidator(0), MaxValueValidator(10)]
    )
    sweetness = models.PositiveIntegerField(
        "Сладость", null=True, blank=True, default=None,
        validators=[MinValueValidator(0), MaxValueValidator(10)]
    )
    flavor_description_html = models.TextField("Описание вкуса (HTML с баджами)", blank=True)
    # tags = models.ManyToManyField(Tag, blank=True, verbose_name="Теги")
    flavor_notes = models.ManyToManyField(FlavorNote, blank=True, verbose_name="Вкусовые нотки")
    brew_methods = models.ManyToManyField(BrewMethod, blank=True, verbose_name="Способы приготовления")
    related_products = models.ManyToManyField(
        "self", blank=True, symmetrical=False,
        verbose_name="Похожие товары",
    )
    main_image = ProcessedImageField(
        upload_to="products/",
        processors=[ResizeToFit(1200, 1200)],
        format="WEBP",
        options={"quality": 90},
        blank=True, null=True,
        verbose_name="Главное фото",
    )
    is_active = models.BooleanField("Активен", default=True, db_index=True)
    is_featured = models.BooleanField("Рекомендуем", default=False)
    is_new = models.BooleanField("Новинка", default=False)
    is_bestseller = models.BooleanField("Хит продаж", default=False)
    is_microlot = models.BooleanField("Микролот", default=False, help_text="Ограниченная серия: подарочное, коллекционное, для гурманов")
    in_stock = models.BooleanField("В наличии", default=True, db_index=True)
    rating_avg = models.DecimalField(
        "Средний рейтинг", max_digits=3, decimal_places=2, default=0,
    )
    reviews_count = models.PositiveIntegerField("Кол-во отзывов", default=0)
    seo_title = models.CharField("SEO Title", max_length=255, blank=True)
    seo_description = models.TextField("SEO Description", blank=True)
    created_at = models.DateTimeField("Создан", auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField("Обновлён", auto_now=True)
    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["category", "is_active"]),
            models.Index(fields=["created_at"]),
        ]
    def __str__(self):
        return self.name
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)
    @property
    def flavor_notes_list(self):
        return ", ".join(self.flavor_notes.values_list("name", flat=True))
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse("catalog:coffee_detail", kwargs={"slug": self.slug})

    @property
    def primary_image(self):
        if self.main_image:
            return self.main_image
        first_gallery_image = self.images.first()
        if first_gallery_image:
            return first_gallery_image.image
        return None

    @property
    def priced_packagings(self):
        """Фасовки, у которых есть хотя бы один вариант (продаваемые) — 1.7.

        Используется для кнопок фасовок на плитке/карточке: гарантирует, что у
        каждой показанной фасовки есть комбинации помол×обжарка (нет пустого
        выпадающего списка). Работает с prefetch (packagings, variants).
        """
        weights_with_variants = {v.weight for v in self.variants.all() if v.weight}
        result = [
            p for p in self.packagings.all()
            if p.weight and p.weight in weights_with_variants
        ]
        return sorted(result, key=lambda p: (p.order, p.weight))

    def belongs_to_section(self, *slugs):
        """Проверяет раздел товара независимо от глубины дерева категорий."""
        category = self.category
        visited = set()
        while category and category.pk not in visited:
            visited.add(category.pk)
            if category.slug in slugs:
                return True
            category = category.parent
        return False

    @property
    def is_coffee_product(self):
        return self.belongs_to_section("kofe", "coffee")

    @property
    def has_body_profile(self):
        return self.body is not None

    @property
    def has_acidity_profile(self):
        return self.acidity is not None

    @property
    def has_taste_profile(self):
        return self.has_body_profile or self.has_acidity_profile

    @property
    def has_packaging_options(self):
        return bool(self.priced_packagings)

    @property
    def has_grind_options(self):
        return any(
            variant.grind_type_id or variant.roast_type_id
            for variant in self.variants.all()
        )

    @property
    def has_purchase_options(self):
        return self.has_packaging_options or self.has_grind_options

class GrindType(models.Model):
    """Справочник «помол» (1.7.3). Любое число значений."""
    name = models.CharField("Помол", max_length=100, unique=True)
    slug = models.SlugField("Адрес в URL", max_length=100, unique=True)
    order = models.PositiveIntegerField("Порядок", default=0, db_index=True)
    is_active = models.BooleanField("Активен", default=True)

    class Meta:
        verbose_name = "Тип помола"
        verbose_name_plural = "Помол (справочник)"
        ordering = ["order", "name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)


class RoastType(models.Model):
    """Справочник «обжарка» (1.7.3). Включает «Без обжарки» (зелёный, 1.7.2)."""
    name = models.CharField("Обжарка", max_length=100, unique=True)
    slug = models.SlugField("Адрес в URL", max_length=100, unique=True)
    order = models.PositiveIntegerField("Порядок", default=0, db_index=True)
    is_active = models.BooleanField("Активна", default=True)

    class Meta:
        verbose_name = "Тип обжарки"
        verbose_name_plural = "Обжарка (справочник)"
        ordering = ["order", "name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)


class ProductPackaging(models.Model):
    """Фасовка (вес+цена) — единственный носитель цены товара (1.7.1)."""
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE,
        related_name="packagings", verbose_name="Товар",
    )
    weight = models.PositiveIntegerField(
        "Вес (г)", null=True, blank=True,
        help_text="Не заполняйте, если товар продаётся без фасовки по весу.",
    )
    price = models.DecimalField("Цена", max_digits=10, decimal_places=2)
    old_price = models.DecimalField(
        "Старая цена", max_digits=10, decimal_places=2,
        null=True, blank=True,
    )
    order = models.PositiveIntegerField("Порядок", default=0, db_index=True)
    is_active = models.BooleanField("Активна", default=True)

    class Meta:
        verbose_name = "Фасовка"
        verbose_name_plural = "Фасовки"
        unique_together = [("product", "weight")]
        ordering = ["order", "weight"]

    def __str__(self):
        if self.weight:
            return f"{self.product.name} — {self.weight} г"
        return f"{self.product.name} — без фасовки"

    @property
    def discount_percent(self):
        if self.old_price and self.price and self.old_price > self.price:
            return int(round(100 - (self.price / self.old_price * 100)))
        return 0


class ProductVariant(models.Model):
    """Вариант товара = фасовка × помол × обжарка (склад) — 1.7.4.

    Цена/вес денормализованы из packaging (price/weight колонки синхронизируются
    в save()), чтобы сортировка по цене и существующие шаблоны/корзина работали.
    """
    # Совместимость со старым кодом, ссылающимся на GRIND_CHOICES.
    GRIND_WHOLE = "whole"
    GRIND_CHOICES = [
        ("whole", "В зёрнах"),
        ("fine", "Мелкий"),
        ("medium", "Средний"),
        ("coarse", "Крупный"),
    ]
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE,
        related_name="variants", verbose_name="Товар",
    )
    packaging = models.ForeignKey(
        ProductPackaging, on_delete=models.CASCADE,
        related_name="variants", verbose_name="Фасовка",
        null=True, blank=True,
    )
    grind_type = models.ForeignKey(
        GrindType, on_delete=models.PROTECT,
        related_name="variants", verbose_name="Помол",
        null=True, blank=True,
    )
    roast_type = models.ForeignKey(
        RoastType, on_delete=models.PROTECT,
        related_name="variants", verbose_name="Обжарка",
        null=True, blank=True,
    )
    # Денормализованные из packaging (заполняются в save()).
    weight = models.PositiveIntegerField("Вес (г)", default=0)
    price = models.DecimalField("Цена", max_digits=10, decimal_places=2, default=0)
    old_price = models.DecimalField(
        "Старая цена", max_digits=10, decimal_places=2,
        null=True, blank=True,
    )
    stock_qty = models.PositiveIntegerField("Остаток на складе", default=0)
    sku = models.CharField("Артикул", max_length=100, blank=True, unique=True, null=True)
    is_preorder = models.BooleanField("Предзаказ", default=False)

    class Meta:
        verbose_name = "Вариант товара"
        verbose_name_plural = "Варианты товара"
        unique_together = [("packaging", "grind_type", "roast_type")]
        ordering = ["weight", "grind_type__order", "roast_type__order"]

    def __str__(self):
        bits = [self.product.name]
        if self.weight:
            bits.append(f"{self.weight}г")
        if self.grind_type_id:
            bits.append(self.grind_type.name)
        if self.roast_type_id:
            bits.append(self.roast_type.name)
        return " ".join(bits)

    def save(self, *args, **kwargs):
        # Синхронизируем денормализованные цену/вес из фасовки.
        if self.packaging_id:
            self.weight = self.packaging.weight or 0
            self.price = self.packaging.price
            self.old_price = self.packaging.old_price
        super().save(*args, **kwargs)

    # Совместимость со старым шаблоном (variant.grind / get_grind_display).
    @property
    def grind(self):
        return self.grind_type.slug if self.grind_type_id else ""

    def get_grind_display(self):
        return self.grind_type.name if self.grind_type_id else ""

    @property
    def roast_display(self):
        return self.roast_type.name if self.roast_type_id else ""

    @property
    def available(self):
        return self.stock_qty > 0 or self.is_preorder

    @property
    def effective_price(self):
        # Цена живёт на фасовке (1.7.1).
        if self.packaging_id:
            return self.packaging.price
        return self.price or None

    @property
    def effective_old_price(self):
        op = self.packaging.old_price if self.packaging_id else self.old_price
        base = self.effective_price
        if op and base and op > base:
            return op
        return None

    @property
    def effective_discount_percent(self):
        base_price = self.effective_price
        old_price = self.effective_old_price
        if old_price and base_price and old_price > base_price:
            return int(round(100 - (base_price / old_price * 100)))
        return 0

    @property
    def discount_percent(self):
        return self.effective_discount_percent
class ProductImage(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE,
        related_name="images", verbose_name="Товар",
    )
    image = ProcessedImageField(
        upload_to="products/gallery/",
        processors=[ResizeToFit(1200, 1200)],
        format="WEBP",
        options={"quality": 85},
        verbose_name="Изображение",
    )
    alt = models.CharField("Alt текст", max_length=255, blank=True)
    order = models.PositiveIntegerField("Порядок", default=0)
    class Meta:
        verbose_name = "Фото товара"
        verbose_name_plural = "Фото товара"
        ordering = ["order"]
    def __str__(self):
        return f"Фото {self.product.name}"
# class Recipe(models.Model):
#     DIFF_EASY = "easy"
#     DIFF_MEDIUM = "medium"
#     DIFF_HARD = "hard"
#     DIFFICULTY_CHOICES = [
#         (DIFF_EASY, "Простой"),
#         (DIFF_MEDIUM, "Средний"),
#         (DIFF_HARD, "Сложный"),
#     ]
#     name = models.CharField("Название", max_length=300)
#     slug = models.SlugField("Адрес в URL", unique=True, db_index=True)
#     brew_method = models.ForeignKey(
#         BrewMethod, on_delete=models.SET_NULL,
#         null=True, blank=True,
#         related_name="recipes",
#         verbose_name="Способ приготовления",
#     )
#     difficulty = models.CharField(
#         "Сложность", max_length=10,
#         choices=DIFFICULTY_CHOICES, default=DIFF_MEDIUM,
#     )
#     time_minutes = models.PositiveIntegerField("Время (мин)")
#     description = RichTextUploadingField("Описание", blank=True)
#     ingredients = models.JSONField(
#         "Ингредиенты",
#         default=list,
#         help_text='Введите корректный JSON, например: ["вода", "кофе", "молоко"].',
#     )
#     main_image = ProcessedImageField(
#         upload_to="recipes/",
#         processors=[ResizeToFit(1200, 800)],
#         format="WEBP",
#         options={"quality": 85},
#         blank=True, null=True,
#         verbose_name="Главное изображение",
#     )
#     video_url = models.URLField("Ссылка на видео", blank=True)
#     products = models.ManyToManyField(
#         Product, blank=True,
#         related_name="recipes",
#         verbose_name="Подходящие товары",
#     )
#     is_published = models.BooleanField("Опубликован", default=False)
#     # 2.3 — рецепты как на исходнике: добавляет покупатель, получивший товар.
#     # Добавление из админки заморожено до запуска MVP (см. ТЗ 2.3).
#     author = models.ForeignKey(
#         settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
#         null=True, blank=True,
#         related_name="recipes",
#         verbose_name="Автор (покупатель)",
#     )
#     is_user_submitted = models.BooleanField(
#         "Добавлен покупателем", default=False,
#         help_text="Рецепт добавлен пользователем, получившим товар (а не из админки).",
#     )
#     created_at = models.DateTimeField("Создан", auto_now_add=True)
#     updated_at = models.DateTimeField("Обновлён", auto_now=True)
#     class Meta:
#         verbose_name = "Рецепт"
#         verbose_name_plural = "Рецепты"
#         ordering = ["-created_at"]
#     def __str__(self):
#         return self.name
# class RecipeStep(models.Model):
#     KIND_ACTION = "action"
#     KIND_POUR = "pour"
#     KIND_CHOICES = [
#         (KIND_ACTION, "Действие"),
#         (KIND_POUR, "Вливание"),
#     ]
#     recipe = models.ForeignKey(
#         Recipe, on_delete=models.CASCADE,
#         related_name="steps", verbose_name="Рецепт",
#     )
#     step_number = models.PositiveSmallIntegerField("Номер шага")
#     kind = models.CharField("Тип шага", max_length=10, choices=KIND_CHOICES, default=KIND_ACTION)
#     time_seconds = models.PositiveIntegerField("Время от начала, сек", default=0)
#     water_ml = models.PositiveIntegerField("Объём воды, мл", default=0)
#     description = models.TextField("Описание шага")
#     image = ProcessedImageField(
#         upload_to="recipes/steps/",
#         processors=[ResizeToFit(800, 600)],
#         format="WEBP",
#         options={"quality": 80},
#         blank=True, null=True,
#         verbose_name="Изображение шага",
#     )
#     class Meta:
#         verbose_name = "Шаг рецепта"
#         verbose_name_plural = "Шаги рецепта"
#         ordering = ["step_number"]
#         unique_together = [("recipe", "step_number")]
#     def __str__(self):
#         return f"{self.recipe.name} — Шаг {self.step_number}"
class Review(models.Model):
    STATUS_NEW = "new"
    STATUS_PUBLISHED = "published"
    STATUS_UNPUBLISHED = "unpublished"

    STATUS_CHOICES = [
        (STATUS_NEW, "Новый"),
        (STATUS_PUBLISHED, "Опубликован"),
        (STATUS_UNPUBLISHED, "Не опубликован"),
    ]

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE,
        related_name="reviews", verbose_name="Товар",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="reviews", verbose_name="Пользователь",
    )
    author_name = models.CharField("Имя автора", max_length=200, blank=True)
    rating = models.PositiveSmallIntegerField(
        "Рейтинг",
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    delivery_rating = models.PositiveSmallIntegerField(
        "Рейтинг доставки", null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Оценка доставки (1-5). Если не заполнено — не учитывается.",
    )
    text = models.TextField("Текст отзыва")
    delivery_text = models.TextField("Текст отзыва о доставке", blank=True, default="")
    delivery_operator = models.CharField(
        "Оператор доставки", max_length=100, blank=True, default="",
        help_text="Например: Aspect Coffee, СДЭК, Почта России, OZON, WB",
    )
    status = models.CharField(
        "Статус",
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_NEW,
        db_index=True,
    )
    is_approved = models.BooleanField("Одобрен", default=False, db_index=True)
    created_at = models.DateTimeField("Дата", auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Отзыв"
        verbose_name_plural = "Отзывы"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["product", "is_approved"])]

    def __str__(self):
        return f"Отзыв на {self.product.name} ({self.rating}★)"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        old_status = None
        if not is_new:
            old_status = Review.objects.filter(pk=self.pk).values_list("status", flat=True).first()

        self.is_approved = (self.status == self.STATUS_PUBLISHED)
        if kwargs.get("update_fields") is not None:
            kwargs["update_fields"] = set(kwargs["update_fields"]) | {"is_approved"}
        super().save(*args, **kwargs)

        from django.db import transaction
        if is_new:
            from apps.catalog.tasks import send_admin_new_review_notification
            transaction.on_commit(lambda: send_admin_new_review_notification.delay(self.pk))
        elif old_status and old_status != self.status:
            if self.status == self.STATUS_PUBLISHED:
                from apps.catalog.tasks import send_user_review_published_notification
                transaction.on_commit(lambda: send_user_review_published_notification.delay(self.pk))
            elif self.status == self.STATUS_UNPUBLISHED:
                from apps.catalog.tasks import send_user_review_rejected_notification
                transaction.on_commit(lambda: send_user_review_rejected_notification.delay(self.pk))

# class ParserLog(models.Model):
#     STATUS_CHOICES = [
#         ("running", "Запущен"),
#         ("success", "Успешно"),
#         ("failed", "Ошибка"),
#     ]
#     started_at = models.DateTimeField("Начало", auto_now_add=True)
#     finished_at = models.DateTimeField("Конец", null=True, blank=True)
#     status = models.CharField("Статус", max_length=20, choices=STATUS_CHOICES, default="running")
#     total_products = models.PositiveIntegerField("Всего товаров", default=0)
#     created_count = models.PositiveIntegerField("Создано", default=0)
#     updated_count = models.PositiveIntegerField("Обновлено", default=0)
#     errors = models.TextField("Ошибки", blank=True)

#     class Meta:
#         verbose_name = "Лог парсера"
#         verbose_name_plural = "Логи парсера"
#         ordering = ["-started_at"]

#     def __str__(self):
#         return f"Парсинг {self.started_at.strftime('%Y-%m-%d %H:%M')} — {self.get_status_display()}"

# class ParserSetting(models.Model):
#     is_auto_update_enabled = models.BooleanField("Автоматическое обновление", default=True)
#     last_run_at = models.DateTimeField("Последний запуск", null=True, blank=True)
#     update_interval_hours = models.PositiveIntegerField("Интервал обновления (часы)", default=24)

#     class Meta:
#         verbose_name = "Настройка парсера"
#         verbose_name_plural = "Настройки парсера"

#     def __str__(self):
#         return "Глобальные настройки парсера"

#     def save(self, *args, **kwargs):
#         self.pk = 1 # Singleton
#         super().save(*args, **kwargs)

#     @classmethod
#     def load(cls):
#         obj, _ = cls.objects.get_or_create(pk=1)
#         return obj


class SiteSettings(models.Model):
    """Singleton model for global site settings (external links, contacts).

    Bug 11: replaces hardcoded URLs in templates so they can be edited via admin.
    """
    site_name = models.CharField(
        "Название сайта",
        max_length=120,
        default="Aspect Coffee",
        help_text="Используется в конструкции Title всех страниц: «{SEO заголовок} — {Название сайта}».",
    )
    # wholesale_url = models.URLField(
    #     "Оптовый сайт",
    #     default="https://aspectcoffee.ru/?utm_source=im",
    #     help_text="Внешняя ссылка на оптовый сайт",
    # )
    # main_site_url = models.URLField(
    #     "Основной сайт бренда",
    #     default="https://aspectcoffee.ru",
    #     help_text="Базовая ссылка на основной сайт (О компании, Достижения и т.д.). Без / в конце.",
    # )
    contact_phone = models.CharField("Телефон", max_length=32, default="+78003334980", blank=True)
    contact_email = models.EmailField(
        "Email сайта для заявок", blank=True, default="",
        help_text="Получатель контактных форм, партнёрских заявок и запросов подписки. Пусто — CONTACT_EMAIL или адрес отправителя из настроек сервера.",
    )
    contact_telegram = models.CharField("Telegram", max_length=200, default="", blank=True)
    contact_whatsapp = models.CharField("WhatsApp", max_length=200, default="https://api.whatsapp.com/send?phone=79508382000", blank=True)
    free_delivery_min = models.PositiveIntegerField("Бесплатная доставка от (₽)", default=2500)
    enable_city_courier = models.BooleanField(
        "Курьер по городу (своя доставка)",
        default=False,
        help_text="Включайте только если у магазина есть собственная курьерская доставка.",
    )
    enable_pickup = models.BooleanField(
        "Самовывоз",
        default=False,
        help_text="Показывает покупателю вариант самовывоза из магазина.",
    )
    enable_cdek_pvz = models.BooleanField(
        "СДЭК — до пункта выдачи",
        default=True,
    )
    enable_cdek_door = models.BooleanField(
        "СДЭК — курьером до двери",
        default=True,
    )
    cart_guarantee_text = models.TextField(
        "Гарантия в корзине",
        default="Если кофе не понравится, вернем деньги или заменим на другой.",
        blank=True,
    )
    repeat_order_text = models.CharField(
        "Текст блока повторного заказа",
        max_length=255,
        default="Подписка на регулярную доставку",
        blank=True,
    )
    recurring_payments_enabled = models.BooleanField(
        "Автосписания и повторные заказы",
        default=True,
        help_text=(
            "Разрешает покупателям создавать повторные заказы и включает "
            "обработку запланированных списаний. Администратор может отключить "
            "функцию глобально в любой момент."
        ),
    )
    payment_timeout_minutes = models.PositiveIntegerField(
        "Таймаут оплаты (минут)",
        default=10,
        help_text="Время на оплату заказа в минутах. Если оплата не поступила, заказ будет автоматически отменён.",
    )
    success_title = models.CharField(
        "Заголовок страницы успешного заказа",
        max_length=120,
        default="Заказ оформлен!",
        blank=True,
    )
    success_message = models.TextField(
        "Текст страницы успешного заказа",
        default="Спасибо за ваш выбор. Мы уже начали готовить посылку.",
        blank=True,
    )
    success_footer = models.CharField(
        "Подпись страницы успешного заказа",
        max_length=160,
        default="Aspect Coffee • Fresh Roasting Daily",
        blank=True,
    )
    # allow_recipe_without_order = models.BooleanField(
    #     "Разрешить добавление рецептов без заказа",
    #     default=False,
    #     help_text="Если включено, авторизованные п��льзователи могут добавлять рецепты без оформленного заказа.",
    # )
    default_storage_description = RichTextUploadingField(
        "Шаблонное описание хранения",
        blank=True,
        help_text="Используется, если у товара не заполнено поле «Хранение».",
    )
    default_delivery_description = RichTextUploadingField(
        "Шаблонное описание доставки",
        blank=True,
        help_text="Используется, если у товара не заполнено поле «Доставка».",
    )
    # roast_banner_is_active = models.BooleanField(
    #     "Показывать баннер обжарки",
    #     default=True,
    #     help_text="Если выключено, горизонтальный черный баннер с таймером на главной странице будет скрыт.",
    # )
    # roast_banner_title = models.CharField(
    #     "Заголовок баннера обжарки",
    #     max_length=255,
    #     default="Мы обжариваем кофе каждый день — следующая обжарка через",
    #     blank=True,
    # )
    # roast_banner_subtitle = models.CharField(
    #     "Подзаголовок баннера обжарки",
    #     max_length=255,
    #     default="Заказывайте сейчас — отправим в день обжарки",
    #     blank=True,
    # )
    # openness_title = models.CharField(
    #     "Заголовок блока открытости",
    #     max_length=200,
    #     default="Полная открытость",
    #     blank=True,
    # )
    # openness_description = models.TextField(
    #     "Описание блока открытости",
    #     default="Мы запустили круглосуточную трансляцию из нашего цеха обжарки и склада зелёного кофе, потому что нам нечего скрывать — у нас всегда полный порядок.",
    #     blank=True,
    # )
    # openness_stream_1_title = models.CharField(
    #     "Название стрима 1",
    #     max_length=100,
    #     default="Цех обжарки",
    #     blank=True,
    # )
    # openness_stream_1_url = models.CharField(
    #     "Ссылка стрима 1",
    #     max_length=500,
    #     default="#",
    #     blank=True,
    # )
    # openness_stream_1_image = models.ImageField(
    #     "Превью стрима 1",
    #     upload_to="openness/",
    #     blank=True,
    #     null=True,
    #     help_text="Фоновое изображение для карточки стрима 1. Если не указано — используется изображение по умолчанию.",
    # )
    # openness_stream_2_title = models.CharField(
    #     "Название стрима 2",
    #     max_length=100,
    #     default="Цех упаковки",
    #     blank=True,
    # )
    # openness_stream_2_url = models.CharField(
    #     "Ссылка стрима 2",
    #     max_length=500,
    #     default="#",
    #     blank=True,
    # )
    # openness_stream_2_image = models.ImageField(
    #     "Превью стрима 2",
    #     upload_to="openness/",
    #     blank=True,
    #     null=True,
    #     help_text="Фоновое изображение для карточки стрима 2. Если не указано — используется изображение по умолчанию.",
    # )
    # openness_stream_3_title = models.CharField(
    #     "Название стрима 3",
    #     max_length=100,
    #     default="Склад зелёного кофе",
    #     blank=True,
    # )
    # openness_stream_3_url = models.CharField(
    #     "Ссылка стрима 3",
    #     max_length=500,
    #     default="#",
    #     blank=True,
    # )
    # openness_stream_3_image = models.ImageField(
    #     "Превью стрима 3",
    #     upload_to="openness/",
    #     blank=True,
    #     null=True,
    #     help_text="Фоновое изображение для карточки стрима 3. Если не указано — используется изображение по умолчанию.",
    # )

    class Meta:
        verbose_name = "Настройки сайта"
        verbose_name_plural = "Настройки сайта"

    def __str__(self):
        return "Настройки сайта"

    def enabled_delivery_types(self):
        """Return checkout delivery codes enabled by the administrator."""
        result = []
        if self.enable_city_courier:
            result.append("courier")
        if self.enable_cdek_pvz:
            result.append("cdek_pvz")
        if self.enable_cdek_door:
            result.append("cdek_door")
        if self.enable_pickup:
            result.append("pickup")
        return result

    def default_delivery_type(self):
        enabled = self.enabled_delivery_types()
        return enabled[0] if enabled else ""

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj





class ProductView(models.Model):
    """Лог просмотров карточки товара.

    1.6 — для ситуативных фильтров «Популярный» (просмотры всего) и
    «Сорт недели» (просмотры за неделю). Дедуп по session_key в product_detail.
    """
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE,
        related_name="views", verbose_name="Товар", db_index=True,
    )
    session_key = models.CharField("Ключ сессии", max_length=40, blank=True, db_index=True)
    created_at = models.DateTimeField("Дата", auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Просмотр товара"
        verbose_name_plural = "Просмотры товаров"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["product", "created_at"])]

    def __str__(self):
        return f"Просмотр {self.product_id} @ {self.created_at:%Y-%m-%d %H:%M}"


class CatalogFilterSettings(models.Model):
    """Singleton с управляемыми порогами ситуативных фильтров (1.6)."""

    NEW_PERIOD_CHOICES = [
        ("day", "День"),
        ("week", "Неделя"),
        ("decade", "Декада (10 дней)"),
        ("month", "Месяц"),
        ("quarter", "Квартал"),
        ("halfyear", "Полугодие"),
        ("year", "Год"),
    ]

    SORT_CHOICES = [
        ("-created_at", "Сначала новые"),
        ("-rating_avg", "С высоким рейтингом"),
        ("variants__price", "Сначала дешевле"),
        ("-variants__price", "Сначала дороже"),
    ]

    default_sort = models.CharField(
        "Сортировка по умолчанию", max_length=32,
        choices=SORT_CHOICES, default="-created_at",
        help_text="Базовое значение сортировки; к нему возвращает «Сбросить все фильтры»",
    )

    popular_views_threshold = models.PositiveIntegerField(
        "Популярный: просмотров всего ≥", default=500,
        help_text="Пресеты: 100, 250, 500, 1000, 2000, 5000",
    )
    week_special_views_threshold = models.PositiveIntegerField(
        "Сорт недели: просмотров за неделю ≥", default=1000,
        help_text="Пресеты: 100, 250, 500, 1000, 2000, 5000",
    )
    new_period = models.CharField(
        "Новый: добавлен не ранее", max_length=10,
        choices=NEW_PERIOD_CHOICES, default="week",
    )
    ending_stock_threshold = models.PositiveIntegerField(
        "Заканчивается: остаток каждого варианта ≤", default=10,
        help_text="Товар считается заканчивающимся, если КАЖДЫЙ вариант упаковки имеет остаток ≤ этого значения",
    )
    bestseller_sales_threshold = models.PositiveIntegerField(
        "Х��т продаж: продаж за период ≥", default=10,
        help_text="Пресеты: 10, 20, 50, 100, 500, 1000",
    )
    bestseller_period_days = models.PositiveIntegerField(
        "Хит продаж: период (дней)", default=7,
    )

    class Meta:
        verbose_name = "Настройки фильтров каталога"
        verbose_name_plural = "Настройки фильтров каталога"

    def __str__(self):
        return "Настройки фильтров каталога"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class Cafe(models.Model):
    """Точка продаж / кафе, где можно попробовать кофе (3.9)."""
    name = models.CharField("Название", max_length=200)
    slug = models.SlugField("Адрес в URL", max_length=200, unique=True)
    address = models.CharField("Адрес", max_length=300)
    city = models.CharField("Город", max_length=100, default="Москва")
    latitude = models.DecimalField("Широта", max_digits=9, decimal_places=6)
    longitude = models.DecimalField("Долгота", max_digits=9, decimal_places=6)
    phone = models.CharField("Телефон", max_length=32, blank=True)
    working_hours = models.CharField("Часы работы", max_length=100, blank=True, default="10:00–22:00")
    description = models.TextField("Описание", blank=True)
    image = ProcessedImageField(
        upload_to="cafes/",
        processors=[ResizeToFit(800, 600)],
        format="WEBP",
        options={"quality": 85},
        blank=True, null=True,
        verbose_name="Фото",
    )
    products = models.ManyToManyField(
        Product, blank=True,
        related_name="cafes",
        verbose_name="Доступные товары",
    )
    is_active = models.BooleanField("Активна", default=True)
    order = models.PositiveIntegerField("Порядок", default=0, db_index=True)
    created_at = models.DateTimeField("Создана", auto_now_add=True)

    class Meta:
        verbose_name = "Точка продаж"
        verbose_name_plural = "Точки продаж"
        ordering = ["order", "name"]

    def __str__(self):
        return f"{self.name} — {self.address}"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)


class NavMenuItem(models.Model):
    """Дополнительные пункты меню «Купить» (Bug-fix: управляется из админки).

    Позволяет добавлять/редактировать/сортировать произвольные ссылки
    в выпадающем меню «Купить» без правки шаблона.
    """

    title = models.CharField("Название", max_length=200)
    url = models.CharField(
        "URL", max_length=500,
        help_text="Относительный путь (например /catalog/?category=chocolate) или полный URL.",
    )
    order = models.PositiveIntegerField("Порядок", default=0, db_index=True)
    is_active = models.BooleanField("Активен", default=True)
    open_in_new_tab = models.BooleanField(
        "Открывать в новой вкладке", default=False,
        help_text="Включите для внешних ссылок (например, на оптовый сайт).",
    )
    show_external_icon = models.BooleanField(
        "Показывать иконку внешней ссылки", default=False,
    )

    class Meta:
        verbose_name = "Пункт меню «Купить»"
        verbose_name_plural = "Пункты меню «Купить»"
        ordering = ["order", "title"]

    def __str__(self):
        return self.title


class PromoSlide(models.Model):
    """Слайд промо-баннера «Журнал» на главной странице.

    Слайды отображаются в карусели рядом с «Сортами недели».
    Первый (USP) слайд захардкожен в шаблоне; остальные берутся из БД.
    """

    section_label = models.CharField(
        "Подпись раздела",
        max_length=100,
        default="Журнал о кофе",
        help_text="Маленький текст над заголовком (напр. «Журнал о кофе»).",
    )
    title = models.CharField("Заголовок", max_length=300)
    link_url = models.CharField(
        "URL кнопки",
        max_length=500,
        blank=True,
        help_text="Например /blog/kak-vybrat-kofe/. Если пусто — кнопка не показывается.",
    )
    link_text = models.CharField(
        "Текст кнопки",
        max_length=100,
        default="Читать статью",
        blank=True,
    )
    background_image_url = models.URLField(
        "URL фонового изображения",
        max_length=1000,
        blank=True,
        help_text="Прямая ссылка на картинку (CDN, Yandex Object Storage и т.д.).",
    )
    background_image = ProcessedImageField(
        verbose_name="Фоновое изображение (загрузить)",
        upload_to="promo_slides/",
        processors=[ResizeToFill(1024, 600)],
        format="WEBP",
        options={"quality": 85},
        blank=True,
        null=True,
        help_text="Если заполнен URL выше — загруженный файл игнорируется.",
    )
    image_opacity = models.FloatField(
        "Прозрачность фона",
        default=0.6,
        help_text="От 0.0 (полностью прозрачный) до 1.0 (непрозрачный).",
    )
    is_usp = models.BooleanField(
        "Является USP/УТП слайдом",
        default=False,
        help_text="Если отмечено, то слайд будет отображаться в стиле УТП (черный фон, три строки текста, без кнопки).",
    )
    usp_line_1_html = models.TextField(
        "Первая строка УТП (HTML)",
        blank=True,
        default='До ближайшей обжарки <b class="font-din-black block"><span x-text="hours">15</span> часов</b>',
    )
    usp_line_2_html = models.TextField(
        "Вторая строка УТП (HTML)",
        blank=True,
        default='<span class="font-din-black block">Бесплатно</span> доставляем',
    )
    usp_line_3_html = models.TextField(
        "Третья строка УТП (HTML)",
        blank=True,
        default='<b class="font-din-black block">Вернем деньги, </b> если кофе не понравится',
    )
    order = models.PositiveIntegerField("Порядок", default=0, db_index=True)
    is_active = models.BooleanField("Активен", default=True)

    class Meta:
        verbose_name = "Промо-слайд (Журнал)"
        verbose_name_plural = "Промо-слайды (Журнал)"
        ordering = ["order"]

    def __str__(self):
        return f"#{self.order} — {self.title[:60]}"

    def get_bg_url(self):
        """Возвращает итоговый URL фонового изображения."""
        if self.background_image_url:
            return self.background_image_url
        if self.background_image:
            return self.background_image.url
        if self.is_usp:
            return f"{settings.STATIC_URL}images/BUp1m_mb.png"
        return ""
