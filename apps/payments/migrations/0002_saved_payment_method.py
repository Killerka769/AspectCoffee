from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("payments", "0001_initial")]

    operations = [
        migrations.AddField(model_name="payment", name="card_last4", field=models.CharField(blank=True, max_length=4, verbose_name="Последние 4 цифры карты")),
        migrations.AddField(model_name="payment", name="payment_method_saved", field=models.BooleanField(default=False, verbose_name="Способ оплаты сохранён")),
        migrations.AddField(model_name="payment", name="payment_method_type", field=models.CharField(blank=True, max_length=32, verbose_name="Тип способа оплаты")),
        migrations.AddField(model_name="payment", name="saved_payment_method_id", field=models.CharField(blank=True, db_index=True, max_length=100, verbose_name="Сохранённый способ оплаты ЮKassa")),
    ]
