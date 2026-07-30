import re

from django.contrib import admin


latin = re.compile(r"[A-Za-z]")
cyrillic = re.compile(r"[А-Яа-яЁё]")


def is_english(value):
    text = str(value)
    return bool(latin.search(text)) and not cyrillic.search(text)


for model in sorted(admin.site._registry, key=lambda item: item._meta.label_lower):
    opts = model._meta
    if is_english(opts.verbose_name) or is_english(opts.verbose_name_plural):
        print(
            "MODEL|"
            f"{opts.label}|{opts.app_config.verbose_name}|"
            f"{opts.verbose_name}|{opts.verbose_name_plural}"
        )
    for field in opts.fields:
        if is_english(field.verbose_name):
            print(f"FIELD|{opts.label}|{field.name}|{field.verbose_name}")
