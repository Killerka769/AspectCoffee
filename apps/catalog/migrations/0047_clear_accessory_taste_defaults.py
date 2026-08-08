from django.db import migrations


ACCESSORY_SECTION_SLUGS = {"aksessuary", "accessories"}


def clear_accessory_taste_defaults(apps, schema_editor):
    Category = apps.get_model("catalog", "Category")
    Product = apps.get_model("catalog", "Product")

    categories = {
        category.pk: (category.slug, category.parent_id)
        for category in Category.objects.all().only("pk", "slug", "parent_id")
    }

    def is_accessory(category_id):
        visited = set()
        while category_id and category_id not in visited:
            visited.add(category_id)
            slug, category_id = categories.get(category_id, (None, None))
            if slug in ACCESSORY_SECTION_SLUGS:
                return True
        return False

    accessory_product_ids = [
        product_id
        for product_id, category_id in Product.objects.values_list("pk", "category_id")
        if is_accessory(category_id)
    ]

    # Старые импортированные аксессуары получили технический кофейный профиль
    # 5/5/5. Удаляем только эту комбинацию, не затрагивая значения, которые
    # администратор мог заполнить осознанно.
    Product.objects.filter(
        pk__in=accessory_product_ids,
        body=5,
        acidity=5,
        sweetness=5,
    ).update(body=None, acidity=None, sweetness=None)


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0046_optional_noncoffee_attributes"),
    ]

    operations = [
        migrations.RunPython(
            clear_accessory_taste_defaults,
            migrations.RunPython.noop,
        ),
    ]
