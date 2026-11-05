from django.db import migrations


def seed_data(apps, schema_editor):
    NavMenuItem = apps.get_model("catalog", "NavMenuItem")
    PromoSlide = apps.get_model("catalog", "PromoSlide")

    # Seed NavMenuItem if empty
    if not NavMenuItem.objects.exists():
        NavMenuItem.objects.create(
            title="Шоколад и сиропы",
            url="/catalog/?category=chocolate",
            order=1,
        )
        NavMenuItem.objects.create(
            title="Наборы",
            url="/catalog/?category=giftbox",
            order=2,
        )
        NavMenuItem.objects.create(
            title="Подписка на кофе",
            url="/catalog/?category=subscription",
            order=3,
        )
        NavMenuItem.objects.create(
            title="Подарочный сертификат",
            url="/catalog/?category=gift-certificate",
            order=4,
        )
        NavMenuItem.objects.create(
            title="Кофе в офис",
            url="/coffee-in-office",
            order=5,
        )
        NavMenuItem.objects.create(
            title="Оптовые поставки",
            url="#",
            order=6,
            open_in_new_tab=True,
            show_external_icon=True,
        )

    # Seed PromoSlide if empty
    if not PromoSlide.objects.exists():
        PromoSlide.objects.create(
            section_label="Журнал о кофе",
            title="Как появились первые кофейни",
            link_url="/blog/",
            link_text="Читать статью",
            background_image_url="",
            order=1,
            image_opacity=0.6,
            is_active=True,
        )
        PromoSlide.objects.create(
            section_label="Журнал о кофе",
            title="Как прошла выставка Coffee Tea Cacao Russian Expo — 2026",
            link_url="/blog/",
            link_text="Читать статью",
            background_image_url="",
            order=2,
            image_opacity=0.6,
            is_active=True,
        )


def remove_seed_data(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0027_add_promo_slide"),
    ]

    operations = [
        migrations.RunPython(seed_data, remove_seed_data),
    ]
