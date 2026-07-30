import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
sys.path.insert(0, '/app')
django.setup()
from apps.orders.models import CartItem
print([f.name for f in CartItem._meta.get_fields()])
