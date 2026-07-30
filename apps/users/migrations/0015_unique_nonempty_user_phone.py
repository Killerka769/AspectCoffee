from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0014_user_phone_confirmed"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="user",
            constraint=models.UniqueConstraint(
                condition=~models.Q(phone=""),
                fields=("phone",),
                name="users_unique_nonempty_phone",
            ),
        ),
    ]
