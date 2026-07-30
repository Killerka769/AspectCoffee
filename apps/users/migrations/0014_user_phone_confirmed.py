from django.db import migrations, models


def confirm_existing_phones(apps, schema_editor):
    User = apps.get_model("users", "User")
    User.objects.exclude(phone="").update(phone_confirmed=True)


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0013_alter_bonustransaction_order_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="phone_confirmed",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "Телефон получен от OAuth-провайдера или повторно "
                    "подтверждён пользователем."
                ),
                verbose_name="Телефон подтверждён",
            ),
        ),
        migrations.RunPython(confirm_existing_phones, migrations.RunPython.noop),
    ]
