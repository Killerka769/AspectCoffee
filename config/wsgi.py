
import os
from django.core.wsgi import get_wsgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")
application = get_wsgi_application()

# Gunicorn starts with --preload, so compiling the heaviest public templates
# here removes the one-second cold-render penalty from the first real request.
from django.template.loader import get_template

for template_name in (
    "catalog/index.html",
    "catalog/catalog.html",
    "catalog/detail.html",
    "orders/basket.html",
    "users/profile.html",
    "blog/index.html",
    "blog/detail.html",
):
    get_template(template_name)
