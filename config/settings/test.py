
from .base import *
DEBUG = True
ALLOWED_HOSTS = ['*']
SECRET_KEY = "test-secret-key-not-used-in-production"
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.PBKDF2PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
AXES_ENABLED = False
YOOKASSA_SHOP_ID = "test-shop"
YOOKASSA_SECRET_KEY = "test-secret"
MEDIA_ROOT = BASE_DIR / "media_test"
if not MEDIA_ROOT.exists():
    MEDIA_ROOT.mkdir(parents=True)
