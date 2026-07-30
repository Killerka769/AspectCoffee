import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
sys.path.insert(0, '/app')
django.setup()
from apps.catalog.models import Product
products = Product.objects.exclude(main_image='').exclude(main_image__isnull=True)
missing = 0
found = 0
for p in products[:50]:
    if p.main_image:
        try:
            if os.path.exists(p.main_image.path):
                found += 1
            else:
                missing += 1
                print(f"MISSING FILE: {p.slug} -> {p.main_image.name}")
        except:
            missing += 1
            print(f"ERROR: {p.slug}")
print(f"Checked 50: found={found}, missing={missing}")
