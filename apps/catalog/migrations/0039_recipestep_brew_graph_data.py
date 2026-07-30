from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("catalog", "0038_review_delivery_operator")]

    operations = [
        migrations.AddField(
            model_name="recipestep",
            name="kind",
            field=models.CharField(choices=[("action", "Действие"), ("pour", "Вливание")], default="action", max_length=10, verbose_name="Тип шага"),
        ),
        migrations.AddField(
            model_name="recipestep",
            name="time_seconds",
            field=models.PositiveIntegerField(default=0, verbose_name="Время от начала, сек"),
        ),
        migrations.AddField(
            model_name="recipestep",
            name="water_ml",
            field=models.PositiveIntegerField(default=0, verbose_name="Объём воды, мл"),
        ),
    ]
