from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0025_add_harvest_year_variety"),
    ]

    operations = [
        migrations.CreateModel(
            name="NavMenuItem",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("title", models.CharField(max_length=200, verbose_name="Название")),
                (
                    "url",
                    models.CharField(
                        help_text="Относительный путь (например /catalog/?category=chocolate) или полный URL.",
                        max_length=500,
                        verbose_name="URL",
                    ),
                ),
                (
                    "order",
                    models.PositiveIntegerField(
                        db_index=True, default=0, verbose_name="Порядок"
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(default=True, verbose_name="Активен"),
                ),
                (
                    "open_in_new_tab",
                    models.BooleanField(
                        default=False,
                        help_text="Включите для внешних ссылок (например, на оптовый сайт).",
                        verbose_name="Открывать в новой вкладке",
                    ),
                ),
                (
                    "show_external_icon",
                    models.BooleanField(
                        default=False,
                        verbose_name="Показывать иконку внешней ссылки",
                    ),
                ),
            ],
            options={
                "verbose_name": "Пункт меню «Купить»",
                "verbose_name_plural": "Пункты меню «Купить»",
                "ordering": ["order", "title"],
            },
        ),
    ]
