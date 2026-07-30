from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("pages", "0010_communitypostcomment_parent_reviewcomment_parent"),
    ]

    operations = [
        migrations.AddField(
            model_name="communitypostcomment",
            name="is_approved",
            field=models.BooleanField(db_index=True, default=True, verbose_name="Одобрено"),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="communitypostcomment",
            name="is_approved",
            field=models.BooleanField(db_index=True, default=False, verbose_name="Одобрено"),
        ),
        migrations.AddField(
            model_name="reviewcomment",
            name="is_approved",
            field=models.BooleanField(db_index=True, default=True, verbose_name="Одобрено"),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="reviewcomment",
            name="is_approved",
            field=models.BooleanField(db_index=True, default=False, verbose_name="Одобрено"),
        ),
    ]
