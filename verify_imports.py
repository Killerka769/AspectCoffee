import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
sys.path.insert(0, '/app')
django.setup()
from apps.catalog.tasks import check_product_images
from apps.catalog.management.commands.check_images import Command
print("Task import: OK")
print("Management command import: OK")
