import os

# 1. Add field to SiteSettings
path = '/app/apps/catalog/models.py'
with open(path, 'r') as f:
    content = f.read()

old = """    openness_title = models.CharField(
        "Заголовок блока открытости",
        max_length=200,
        default="Полная открытость",
        blank=True,
    )"""

new = """    email_confirmation_enabled = models.BooleanField(
        "Подтверждение email при регистрации",
        default=True,
        help_text="Если включено, при регистрации отправляется код подтверждения. Без подтверждения вход невозможен.",
    )
    openness_title = models.CharField(
        "Заголовок блока открытости",
        max_length=200,
        default="Полная открытость",
        blank=True,
    )"""

if old in content:
    content = content.replace(old, new)
    with open(path, 'w') as f:
        f.write(content)
    print("OK - added email_confirmation_enabled to SiteSettings")
else:
    print("ERROR: SiteSettings block not found")
