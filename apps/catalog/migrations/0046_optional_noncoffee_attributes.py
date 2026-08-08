from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models


COFFEE_SECTION_SLUGS = {"kofe", "coffee"}
ACCESSORY_SECTION_SLUGS = {"aksessuary", "accessories"}


def clear_inherited_coffee_defaults(apps, schema_editor):
    Category = apps.get_model("catalog", "Category")
    Product = apps.get_model("catalog", "Product")
    ProductPackaging = apps.get_model("catalog", "ProductPackaging")
    ProductVariant = apps.get_model("catalog", "ProductVariant")

    categories = {
        category.pk: (category.slug, category.parent_id)
        for category in Category.objects.all().only("pk", "slug", "parent_id")
    }

    def belongs_to_section(category_id, section_slugs):
        visited = set()
        while category_id and category_id not in visited:
            visited.add(category_id)
            slug, category_id = categories.get(category_id, (None, None))
            if slug in section_slugs:
                return True
        return False

    product_categories = list(
        Product.objects.all().values_list("pk", "category_id")
    )
    noncoffee_product_ids = [
        product_id
        for product_id, category_id in product_categories
        if not belongs_to_section(category_id, COFFEE_SECTION_SLUGS)
    ]
    accessory_product_ids = [
        product_id
        for product_id, category_id in product_categories
        if belongs_to_section(category_id, ACCESSORY_SECTION_SLUGS)
    ]

    # 5/5/0 were technical defaults and created a fake coffee profile on
    # accessories, chocolate and other products outside the coffee section.
    Product.objects.filter(
        pk__in=noncoffee_product_ids,
        body=5,
        acidity=5,
        sweetness=0,
    ).update(body=None, acidity=None, sweetness=None)

    # Only accessories are cleaned automatically. Weight is a legitimate
    # property for tea/chocolate, so it must not be removed outside this section.
    Product.objects.filter(pk__in=accessory_product_ids).update(
        roast_level="",
        processing_method="",
    )
    ProductPackaging.objects.filter(
        product_id__in=accessory_product_ids,
    ).update(weight=None)
    ProductVariant.objects.filter(
        product_id__in=accessory_product_ids,
    ).update(weight=0, grind_type=None, roast_type=None)


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0045_subscription_menu_redirect"),
    ]

    operations = [
        migrations.AlterField(
            model_name="product",
            name="body",
            field=models.PositiveIntegerField(
                blank=True,
                default=None,
                null=True,
                validators=[
                    MinValueValidator(0),
                    MaxValueValidator(10),
                ],
                verbose_name="Плотность (Тельце)",
            ),
        ),
        migrations.AlterField(
            model_name="product",
            name="acidity",
            field=models.PositiveIntegerField(
                blank=True,
                default=None,
                null=True,
                validators=[
                    MinValueValidator(0),
                    MaxValueValidator(10),
                ],
                verbose_name="Кислотность",
            ),
        ),
        migrations.AlterField(
            model_name="product",
            name="sweetness",
            field=models.PositiveIntegerField(
                blank=True,
                default=None,
                null=True,
                validators=[
                    MinValueValidator(0),
                    MaxValueValidator(10),
                ],
                verbose_name="Сладость",
            ),
        ),
        migrations.AlterField(
            model_name="productpackaging",
            name="weight",
            field=models.PositiveIntegerField(
                blank=True,
                help_text=(
                    "Не заполняйте, если товар продаётся без фасовки по весу."
                ),
                null=True,
                verbose_name="Вес (г)",
            ),
        ),
        migrations.RunPython(
            clear_inherited_coffee_defaults,
            migrations.RunPython.noop,
        ),
    ]
