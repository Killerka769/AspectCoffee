import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.prod')
import django
django.setup()
from apps.users.views import register, verify_email, login_view
print('All views imported OK')
print('register:', register)
print('verify_email:', verify_email)
print('login_view:', login_view)
