import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
sys.path.insert(0, '/app')
django.setup()
from apps.catalog.models import Product
products = Product.objects.exclude(main_image='').exclude(main_image__isnull=True)
missing = 0
found = 0
missing_list = []
for p in products:
    if p.main_image:
        try:
            if os.path.exists(p.main_image.path):
                found += 1
            else:
                missing += 1
                missing_list.append(p.slug)
        except:
            missing += 1
            missing_list.append(p.slug)
print(f"Total checked: {found + missing}, found={found}, missing={missing}")
print("Missing slugs:")
for s in missing_list:
    print(f"  {s}")
