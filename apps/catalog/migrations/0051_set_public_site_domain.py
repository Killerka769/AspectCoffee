from django.db import migrations


def set_public_site(apps, schema_editor):
    Site = apps.get_model("sites", "Site")
    site = Site.objects.filter(pk=2).first()
    if site is None:
        Site.objects.create(pk=2, domain="aspectcoffee.ru", name="Aspect Coffee")
    elif site.domain in ("example.com", "example.org"):
        site.domain = "aspectcoffee.ru"
        if site.name in ("example.com", "example.org", ""):
            site.name = "Aspect Coffee"
        site.save(update_fields=["domain", "name"])
    Site.objects.filter(domain="example.com").update(domain="aspectcoffee.ru", name="Aspect Coffee")


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0050_remove_sitesettings_allow_recipe_without_order"),
        ("sites", "0002_alter_domain_unique"),
    ]

    operations = [
        migrations.RunPython(set_public_site, migrations.RunPython.noop),
    ]
