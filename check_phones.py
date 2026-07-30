import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
sys.path.insert(0, '/app')
django.setup()
from apps.users.models import User
users = User.objects.exclude(phone='').exclude(phone__isnull=True)[:10]
for u in users:
    print(f"{u.email}: phone='{u.phone}'")
