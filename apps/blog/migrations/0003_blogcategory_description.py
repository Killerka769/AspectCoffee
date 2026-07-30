from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("blog", "0002_articlebookmark_articlereadhistory"),
    ]

    operations = [
        migrations.AddField(
            model_name="blogcategory",
            name="description",
            field=models.TextField(blank=True, verbose_name="Описание"),
        ),
    ]
