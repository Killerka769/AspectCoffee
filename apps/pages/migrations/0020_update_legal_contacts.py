from django.db import migrations


REPLACEMENTS = (
    ("hello@aspectcoffee.ru", "aspectcoffeeroasters@gmail.com"),
    ("info@aspectcoffee.ru", "aspectcoffeeroasters@gmail.com"),
    ("partners@aspectcoffee.ru", "aspectcoffeeroasters@gmail.com"),
    ("8 (800) 123-45-67", "+7 988 291-93-92"),
    ("8 (800) 333-49-80", "+7 988 291-93-92"),
    ("+7 800 333 49 80", "+7 988 291-93-92"),
    ("+7 800 333-49-80", "+7 988 291-93-92"),
    ("+78003334980", "+79882919392"),
    ("tel:+78003334980", "tel:+79882919392"),
)


def update_legal_contacts(apps, schema_editor):
    LegalDocument = apps.get_model("pages", "LegalDocument")
    for doc in LegalDocument.objects.all():
        content = doc.content or ""
        updated = content
        for old, new in REPLACEMENTS:
            updated = updated.replace(old, new)
        if updated != content:
            doc.content = updated
            doc.save(update_fields=["content"])


def restore_legal_contacts(apps, schema_editor):
    LegalDocument = apps.get_model("pages", "LegalDocument")
    reverse_pairs = (
        ("aspectcoffeeroasters@gmail.com", "hello@aspectcoffee.ru"),
        ("+7 988 291-93-92", "8 (800) 333-49-80"),
        ("tel:+79882919392", "tel:+78003334980"),
        ("+79882919392", "+78003334980"),
    )
    for doc in LegalDocument.objects.all():
        content = doc.content or ""
        updated = content
        for new, old in reverse_pairs:
            updated = updated.replace(new, old)
        if updated != content:
            doc.content = updated
            doc.save(update_fields=["content"])


class Migration(migrations.Migration):

    dependencies = [
        ("pages", "0019_popupmessage_placement"),
    ]

    operations = [
        migrations.RunPython(update_legal_contacts, restore_legal_contacts),
    ]
