from django.db import migrations


def seed_default_usp_slide(apps, schema_editor):
    PromoSlide = apps.get_model("catalog", "PromoSlide")

    if not PromoSlide.objects.filter(is_usp=True).exists():
        PromoSlide.objects.create(
            section_label="До ближайшей обжарки (УТП)",
            title="До ближайшей обжарки (УТП)",
            is_usp=True,
            usp_line_1_html='До ближайшей обжарки <b class="font-din-black block"><span x-text="hours">15</span> часов</b>',
            usp_line_2_html='<span class="font-din-black block">Бесплатно</span> доставляем',
            usp_line_3_html='<b class="font-din-black block">Вернем деньги, </b> если кофе не понравится',
            background_image_url="",
            image_opacity=0.4,
            is_active=True,
            order=0,
        )


def remove_default_usp_slide(apps, schema_editor):
    PromoSlide = apps.get_model("catalog", "PromoSlide")
    PromoSlide.objects.filter(is_usp=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0031_promoslide_is_usp_promoslide_usp_line_1_html_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_default_usp_slide, remove_default_usp_slide),
    ]
