from django.db import migrations, models


NEW_PHONE = "+7 988 291-93-92"
NEW_EMAIL = "aspectcoffeeroasters@gmail.com"
NEW_WHATSAPP = "https://api.whatsapp.com/send?phone=79882919392"

OLD_PHONES = {
    "",
    "+78003334980",
    "78003334980",
    "+7 800 333 49 80",
    "+7 800 333-49-80",
    "8 (800) 333-49-80",
    "8 (800) 123-45-67",
    "+78001234567",
    "88001234567",
}
OLD_EMAILS = {
    "",
    "hello@aspectcoffee.ru",
    "info@aspectcoffee.ru",
    "partners@aspectcoffee.ru",
}
OLD_WHATSAPP = {
    "",
    "https://api.whatsapp.com/send?phone=79508382000",
    "https://wa.me/79508382000",
}


def update_public_contacts(apps, schema_editor):
    SiteSettings = apps.get_model("catalog", "SiteSettings")
    for site in SiteSettings.objects.all():
        fields = []
        if (site.contact_phone or "").strip() in OLD_PHONES:
            site.contact_phone = NEW_PHONE
            fields.append("contact_phone")
        if (site.contact_email or "").strip().lower() in OLD_EMAILS:
            site.contact_email = NEW_EMAIL
            fields.append("contact_email")
        if (site.contact_whatsapp or "").strip() in OLD_WHATSAPP:
            site.contact_whatsapp = NEW_WHATSAPP
            fields.append("contact_whatsapp")
        if fields:
            site.save(update_fields=fields)


def restore_public_contacts(apps, schema_editor):
    SiteSettings = apps.get_model("catalog", "SiteSettings")
    SiteSettings.objects.filter(contact_phone=NEW_PHONE).update(contact_phone="+78003334980")
    SiteSettings.objects.filter(contact_email=NEW_EMAIL).update(contact_email="")
    SiteSettings.objects.filter(contact_whatsapp=NEW_WHATSAPP).update(
        contact_whatsapp="https://api.whatsapp.com/send?phone=79508382000"
    )


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0051_set_public_site_domain"),
    ]

    operations = [
        migrations.AlterField(
            model_name="sitesettings",
            name="contact_phone",
            field=models.CharField(
                blank=True,
                default="+7 988 291-93-92",
                max_length=32,
                verbose_name="Телефон",
            ),
        ),
        migrations.AlterField(
            model_name="sitesettings",
            name="contact_email",
            field=models.EmailField(
                blank=True,
                default="aspectcoffeeroasters@gmail.com",
                max_length=254,
                verbose_name="Email сайта для заявок",
                help_text="Получатель контактных форм, партнёрских заявок и запросов подписки. Пусто — CONTACT_EMAIL или адрес отправителя из настроек сервера.",
            ),
        ),
        migrations.AlterField(
            model_name="sitesettings",
            name="contact_whatsapp",
            field=models.CharField(
                blank=True,
                default="https://api.whatsapp.com/send?phone=79882919392",
                max_length=200,
                verbose_name="WhatsApp",
            ),
        ),
        migrations.RunPython(update_public_contacts, restore_public_contacts),
    ]
