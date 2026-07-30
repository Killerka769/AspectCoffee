from django.db import migrations, models
import imagekit.models.fields


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0026_add_nav_menu_item"),
    ]

    operations = [
        migrations.CreateModel(
            name="PromoSlide",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("section_label", models.CharField(default="Журнал о кофе", help_text="Маленький текст над заголовком (напр. «Журнал о кофе»).", max_length=100, verbose_name="Подпись раздела")),
                ("title", models.CharField(max_length=300, verbose_name="Заголовок")),
                ("link_url", models.CharField(blank=True, help_text="Например /blog/kak-vybrat-kofe/. Если пусто — кнопка не показывается.", max_length=500, verbose_name="URL кнопки")),
                ("link_text", models.CharField(blank=True, default="Читать статью", max_length=100, verbose_name="Текст кнопки")),
                ("background_image_url", models.URLField(blank=True, help_text="Прямая ссылка на картинку (CDN, Yandex Object Storage и т.д.).", max_length=1000, verbose_name="URL фонового изображения")),
                ("background_image", imagekit.models.fields.ProcessedImageField(blank=True, help_text="Если заполнен URL выше — загруженный файл игнорируется.", null=True, upload_to="promo_slides/", verbose_name="Фоновое изображение (загрузить)")),
                ("image_opacity", models.FloatField(default=0.6, help_text="От 0.0 (полностью прозрачный) до 1.0 (непрозрачный).", verbose_name="Прозрачность фона")),
                ("order", models.PositiveIntegerField(db_index=True, default=0, verbose_name="Порядок")),
                ("is_active", models.BooleanField(default=True, verbose_name="Активен")),
            ],
            options={
                "verbose_name": "Промо-слайд (Журнал)",
                "verbose_name_plural": "Промо-слайды (Журнал)",
                "ordering": ["order"],
            },
        ),
    ]
