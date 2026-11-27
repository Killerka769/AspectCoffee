from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pages", "0021_offer_seller_requisites"),
    ]

    operations = [
        # Default only affects new rows. Posts already on the site
        # keep is_published=True and stay visible.
        migrations.AlterField(
            model_name="communitypost",
            name="is_published",
            field=models.BooleanField(db_index=True, default=False, verbose_name="Опубликовано"),
        ),
    ]
