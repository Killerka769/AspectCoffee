from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("blog", "0009_delete_blog_series"),
    ]

    operations = [
        # Default only affects new rows. Comments already on the site
        # keep is_approved=True and stay visible.
        migrations.AlterField(
            model_name="articlecomment",
            name="is_approved",
            field=models.BooleanField(db_index=True, default=False, verbose_name="Опубликован"),
        ),
    ]
