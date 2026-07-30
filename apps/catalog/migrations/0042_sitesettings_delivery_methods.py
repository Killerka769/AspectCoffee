from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0041_review_delivery_rating_review_delivery_text_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="sitesettings",
            name="enable_city_courier",
            field=models.BooleanField(
                default=False,
                help_text="Включайте только если у магазина есть собственная курьерская доставка.",
                verbose_name="Курьер по городу (своя доставка)",
            ),
        ),
        migrations.AddField(
            model_name="sitesettings",
            name="enable_pickup",
            field=models.BooleanField(
                default=False,
                help_text="Показывает покупателю вариант самовывоза из магазина.",
                verbose_name="Самовывоз",
            ),
        ),
        migrations.AddField(
            model_name="sitesettings",
            name="enable_cdek_pvz",
            field=models.BooleanField(default=True, verbose_name="СДЭК — до пункта выдачи"),
        ),
        migrations.AddField(
            model_name="sitesettings",
            name="enable_cdek_door",
            field=models.BooleanField(default=True, verbose_name="СДЭК — курьером до двери"),
        ),
    ]
