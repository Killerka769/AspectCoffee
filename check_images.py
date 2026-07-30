import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
sys.path.insert(0, '/app')
django.setup()

from apps.catalog.models import Product
total = Product.objects.count()
with_img = Product.objects.exclude(main_image='').exclude(main_image__isnull=True).count()
without_img = Product.objects.filter(main_image='').count()
null_img = Product.objects.filter(main_image__isnull=True).count()
print(f"Total: {total}, With image: {with_img}, Empty image: {without_img}, Null image: {null_img}")
no_img = list(Product.objects.filter(main_image='').values_list('slug', 'name')[:15])
for s, n in no_img:
    print(f"  NO IMG: {s} -- {n}")
no_img2 = list(Product.objects.filter(main_image__isnull=True).values_list('slug', 'name')[:15])
for s, n in no_img2:
    print(f"  NULL: {s} -- {n}")
