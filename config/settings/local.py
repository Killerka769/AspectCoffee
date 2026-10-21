"""Loopback-only disposable Docker environment; never production configuration."""
from .dev import *

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "data" / "db.sqlite3", "OPTIONS": {"timeout": 20}}}
