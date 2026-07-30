"""Settings for the isolated test.aspectcoffee.ru environment."""

from decouple import Csv, config

from .prod import *  # noqa: F403


DEBUG = False
ENVIRONMENT = "test"

ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS",
    default="test.aspectcoffee.ru,localhost,127.0.0.1",
    cast=Csv(),
)
CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS",
    default="https://test.aspectcoffee.ru,http://10.88.0.1:8080,http://localhost:8080",
    cast=Csv(),
)
CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="https://test.aspectcoffee.ru",
    cast=Csv(),
)

# Test and production cookies must never overlap in the same browser.
SESSION_COOKIE_NAME = "aspectcoffee_test_sessionid_v2"
CSRF_COOKIE_NAME = "aspectcoffee_test_csrftoken"

# The isolated contour is also verified directly through the IP allowlist on
# port 8080. Secure cookies are still used on the public HTTPS test domain,
# while the internal HTTP QA endpoint can explicitly opt out.
TEST_ALLOW_INSECURE_HTTP = config(
    "TEST_ALLOW_INSECURE_HTTP",
    default=True,
    cast=bool,
)
if TEST_ALLOW_INSECURE_HTTP:
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False

# Mail and external services are inert unless test-only credentials are supplied.
EMAIL_BACKEND = config(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)
DEFAULT_FROM_EMAIL = config(
    "DEFAULT_FROM_EMAIL",
    default="Aspect Coffee TEST <test@aspectcoffee.ru>",
)

# Do not submit the test subdomain to search engines or preload it separately.
SECURE_HSTS_PRELOAD = False
