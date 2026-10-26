#!/bin/sh
set -eu
export SECRET_KEY="${SECRET_KEY:-isolated-checks-not-for-production}"
export DJANGO_SETTINGS_MODULE=config.settings.test
python manage.py check
python manage.py makemigrations --check --dry-run --noinput
python manage.py test --noinput
