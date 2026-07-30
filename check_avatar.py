import os, sys
sys.path.insert(0, '/app')
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.dev'
import django
django.setup()
from apps.users.models import User
u = User.objects.get(email='kaliuser5441@gmail.com')
print('avatar:', u.avatar)
print('has_avatar:', bool(u.avatar))
if u.avatar:
    print('avatar_url:', u.avatar.url)
