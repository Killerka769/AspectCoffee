import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
sys.path.insert(0, '/app')
django.setup()
from apps.users.models import User
u = User.objects.get(email='inspiretd001@gmail.com')
print(f"Phone raw: '{u.phone}'")
print(f"Phone repr: {repr(u.phone)}")
