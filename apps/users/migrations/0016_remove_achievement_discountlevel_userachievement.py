from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0015_unique_nonempty_user_phone"),
    ]

    operations = [
        migrations.DeleteModel(name="UserAchievement"),
        migrations.DeleteModel(name="Achievement"),
        migrations.DeleteModel(name="DiscountLevel"),

        migrations.RemoveField(model_name="user", name="credit_limit"),

        migrations.AlterField(
            model_name="user",
            name="wholesale_discount",
            field=__import__("django.db.models", fromlist=["PositiveIntegerField"]).PositiveIntegerField(
                default=0,
                help_text="Скидка от розничной цены для оптового покупателя",
                verbose_name="Оптовая скидка (%)",
            ),
        ),
    ]