from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Banner",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slot", models.CharField(choices=[("home_weekly", "Главная — над «Сорта недели»"), ("home_top", "Главная — Hero (вверху)"), ("home_bottom", "Главная — внизу")], default="home_weekly", max_length=32, verbose_name="Слот")),
                ("title", models.CharField(max_length=200, verbose_name="Заголовок")),
                ("description", models.CharField(blank=True, max_length=500, verbose_name="Описание")),
                ("image", models.ImageField(blank=True, null=True, upload_to="banners/", verbose_name="Изображение")),
                ("link_url", models.CharField(blank=True, max_length=500, verbose_name="URL")),
                ("button_label", models.CharField(blank=True, default="Перейти", max_length=80, verbose_name="Текст кнопки")),
                ("is_active", models.BooleanField(default=True, verbose_name="Активен")),
                ("order", models.PositiveIntegerField(default=0, verbose_name="Порядок")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "Баннер",
                "verbose_name_plural": "Баннеры",
                "ordering": ["slot", "order", "-created_at"],
            },
        ),
        migrations.CreateModel(
            name="SiteLink",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("group", models.CharField(choices=[("footer_company", "Футер — Компания"), ("footer_help", "Футер — Помощь"), ("footer_catalog", "Футер — Каталог"), ("promo", "Промо-блоки")], max_length=32, verbose_name="Группа")),
                ("label", models.CharField(max_length=120, verbose_name="Название")),
                ("url", models.CharField(max_length=500, verbose_name="URL")),
                ("open_new_tab", models.BooleanField(default=False, verbose_name="В новой вкладке")),
                ("is_active", models.BooleanField(default=True, verbose_name="Активна")),
                ("order", models.PositiveIntegerField(default=0, verbose_name="Порядок")),
            ],
            options={
                "verbose_name": "Ссылка сайта",
                "verbose_name_plural": "Ссылки сайта",
                "ordering": ["group", "order", "label"],
            },
        ),
    ]
