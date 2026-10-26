from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("catalog", "0047_clear_accessory_taste_defaults")]
    operations = [
        migrations.AddField(
            model_name="sitesettings", name="contact_email",
            field=models.EmailField(
                blank=True, default="", max_length=254, verbose_name="Email сайта для заявок",
                help_text="Получатель контактных форм, партнёрских заявок и запросов подписки. Пусто — CONTACT_EMAIL или адрес отправителя из настроек сервера.",
            ),
        ),
    ]
