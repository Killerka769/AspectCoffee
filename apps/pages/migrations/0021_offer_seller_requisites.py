import re

from django.db import migrations


REQUISITES = """
<!-- aspect-requisites -->
<h2>8. Реквизиты Продавца</h2>
<p>Продавец: индивидуальный предприниматель Казиев Ахмед Сулейманович.</p>
<p>
ИНН: 057203224730<br>
ОГРНИП: 325050000191402<br>
Юридический адрес: 367904, Республика Дагестан, г. Махачкала, пгт Тарки, ул. Живописная, д. 70<br>
Расчётный счёт: 40802810600008882759 в АО «ТБанк»<br>
БИК: 044525974<br>
Корреспондентский счёт: 30101810145250000974<br>
ИНН банка: 7710140679<br>
Адрес банка: 127287, г. Москва, ул. Хуторская 2-я, д. 38А, стр. 26
</p>
<!-- /aspect-requisites -->
""".strip()

SELLER_SENTENCE = (
    "Продавцом является ИП Казиев Ахмед Сулейманович "
    "(ИНН 057203224730, ОГРНИП 325050000191402)."
)
BLOCK = re.compile(r"<!-- aspect-requisites -->.*?<!-- /aspect-requisites -->", re.DOTALL)
HEADING = re.compile(r"<h2[^>]*>[^<]*еквизит[\s\S]*?(?=<h2|\Z)", re.IGNORECASE)
SELLER = re.compile(r"Продавцом является[^<]*")
FAKE_COMPANY = "ООО «Aspect Coffee»"
REAL_SELLER = "ИП Казиев Ахмед Сулейманович"


def _with_requisites(content):
    content = content or ""
    content = content.replace("1077847482052", "325050000191402")
    content = content.replace(FAKE_COMPANY, REAL_SELLER)
    content = SELLER.sub(SELLER_SENTENCE, content, count=1)
    if BLOCK.search(content):
        return BLOCK.sub(REQUISITES, content)
    if HEADING.search(content):
        return HEADING.sub(REQUISITES, content, count=1)
    return content.rstrip() + "\n" + REQUISITES


def update_offer(apps, schema_editor):
    LegalDocument = apps.get_model("pages", "LegalDocument")
    offer = LegalDocument.objects.filter(slug="public_offer").first()
    if offer is None:
        return
    offer.content = _with_requisites(offer.content)
    offer.save(update_fields=["content"])
    for doc in LegalDocument.objects.exclude(pk=offer.pk):
        content = (doc.content or "").replace(FAKE_COMPANY, REAL_SELLER)
        if content != (doc.content or ""):
            doc.content = content
            doc.save(update_fields=["content"])


class Migration(migrations.Migration):

    dependencies = [
        ("pages", "0020_update_legal_contacts"),
    ]

    operations = [
        migrations.RunPython(update_offer, migrations.RunPython.noop),
    ]
