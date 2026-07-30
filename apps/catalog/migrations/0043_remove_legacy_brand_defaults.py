from django.db import migrations, models


def normalize_site_settings(apps, schema_editor):
    SiteSettings = apps.get_model("catalog", "SiteSettings")
    SiteSettings.objects.update(
        site_name="Aspect Coffee",
        wholesale_url="https://aspectcoffee.ru/?utm_source=im",
        main_site_url="https://aspectcoffee.ru",
        contact_telegram="",
        success_footer="Aspect Coffee • Fresh Roasting Daily",
    )

    PromoSlide = apps.get_model("catalog", "PromoSlide")
    PromoSlide.objects.filter(is_usp=True).update(background_image_url="")


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0042_sitesettings_delivery_methods"),
    ]

    operations = [
        migrations.AlterField(
            model_name="sitesettings",
            name="contact_telegram",
            field=models.CharField(blank=True, default="", max_length=200, verbose_name="Telegram"),
        ),
        migrations.RunPython(normalize_site_settings, migrations.RunPython.noop),
    ]
