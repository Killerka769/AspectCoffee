from django.db import migrations


def point_subscription_to_page(apps, schema_editor):
    NavMenuItem = apps.get_model("catalog", "NavMenuItem")
    item = NavMenuItem.objects.filter(title__iexact="Подписка на кофе").first()
    if item is None:
        item = NavMenuItem(title="Подписка на кофе", order=50)
    item.url = "/subscription/"
    item.open_in_new_tab = False
    item.show_external_icon = False
    item.is_active = True
    item.save(
        update_fields=[
            "url",
            "open_in_new_tab",
            "show_external_icon",
            "is_active",
        ]
        if item.pk
        else None
    )


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0044_sitesettings_recurring_payments_enabled_and_more"),
    ]

    operations = [
        migrations.RunPython(point_subscription_to_page, migrations.RunPython.noop),
    ]
