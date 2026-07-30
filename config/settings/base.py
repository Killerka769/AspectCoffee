
import os
from pathlib import Path
from decouple import config, Csv
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
BASE_DIR = Path(__file__).resolve().parent.parent.parent
SECRET_KEY = config("SECRET_KEY")
DEBUG = config("DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())
SITE_ID = 2
DJANGO_APPS = [
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.forms",
    "unfold.contrib.import_export",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
]
THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
    "django_filters",
    "axes",
    "imagekit",
    "import_export",
    "ckeditor",
    "ckeditor_uploader",
    "corsheaders",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.yandex",
    "allauth.socialaccount.providers.vk",
    "django_htmx",
]
LOCAL_APPS = [
    "apps.catalog",
    "apps.orders",
    "apps.users",
    "apps.delivery",
    "apps.payments",
    "apps.api",
    "apps.warehouse",
    "apps.pages",
    "apps.blog",
]
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "apps.orders.middleware.GuestCartSessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "apps.users.middleware.OAuthPhoneCompletionMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "axes.middleware.AxesMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]
ROOT_URLCONF = "config.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.orders.context_processors.cart_context",
                "apps.pages.context_processors.site_chrome",
                "apps.catalog.context_processors.nav_sections",
                "apps.catalog.context_processors.published_reviews_count",
                "apps.users.context_processors.phone_countries",
            ],
        },
    },
]
WSGI_APPLICATION = "config.wsgi.application"
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME", default="aspectcoffee"),
        "USER": config("DB_USER", default="postgres"),
        "PASSWORD": config("DB_PASSWORD", default="postgres"),
        "HOST": config("DB_HOST", default="127.0.0.1"),
        "PORT": config("DB_PORT", default="5432", cast=int),
    }
}
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://redis:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
        "TIMEOUT": 300,
    }
}
SESSION_ENGINE = "django.contrib.sessions.backends.db"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LANGUAGE_CODE = "ru-ru"
LANGUAGES = (("ru", "Русский"),)
LOCALE_PATHS = [BASE_DIR / "locale"]
TIME_ZONE = "Europe/Moscow"
ENABLE_API_SYNC = True
USE_TZ = True
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [
    BASE_DIR / "static",
    ("asset", BASE_DIR / "asset"),
]
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
AUTH_USER_MODEL = "users.User"
LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/account/profile/"
LOGOUT_REDIRECT_URL = "/"
AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_ADAPTER = "apps.users.adapters.CustomAccountAdapter"
SOCIALACCOUNT_ADAPTER = "apps.users.adapters.CustomSocialAccountAdapter"
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_EMAIL_VERIFICATION = "none"
SOCIALACCOUNT_LOGIN_ON_GET = True
SOCIALACCOUNT_PROVIDERS = {
    "yandex": {
        "SCOPE": ["login:email", "login:info", "login:default_phone", "login:avatar"],
        # Never silently reuse the previous Yandex browser session.  Yandex
        # displays the consent/account chooser on every new OAuth login, so a
        # user who logged out of Aspect Coffee can select another Yandex ID.
        "AUTH_PARAMS": {"force_confirm": "yes"},
        "FIELDS": [
            "id",
            "login",
            "first_name",
            "last_name",
            "email",
            "default_phone",
            "default_avatar_id",
            "is_avatar_empty",
            "sex",
            "birthday",
        ],
    },
    "vk": {
        "SCOPE": ["email"],
        "VERSION": "5.131",
    },
}
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1
AXES_ENABLED = True
# On lockout, redirect the user to a self-service unlock page (email OTP) instead of
# axes bare text response. AJAX/XHR login attempts still get axes JSON response
# (see axes.helpers.get_lockout_response) - this only affects normal browser requests.
AXES_LOCKOUT_URL = "/unlock-account/"
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.CursorPagination",
    "PAGE_SIZE": 24,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "20/minute",
        "user": "100/minute",
    },
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}
from datetime import timedelta
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": config("JWT_SECRET_KEY", default=SECRET_KEY),
    "AUTH_HEADER_TYPES": ("Bearer",),
}
CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:3000,http://127.0.0.1:3000",
    cast=Csv()
)
SPECTACULAR_SETTINGS = {
    "TITLE": "Aspect Coffee API",
    "DESCRIPTION": "REST API для мобильного клиента интернет-магазина кофе",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
}
EMAIL_BACKEND = config(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)
EMAIL_HOST = config("EMAIL_HOST", default="")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=False, cast=bool)
EMAIL_USE_SSL = config("EMAIL_USE_SSL", default=False, cast=bool)
EMAIL_TIMEOUT = config("EMAIL_TIMEOUT", default=10, cast=int)
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="Aspect Coffee <info@aspectcoffee.ru>")

# Browser Web Push (VAPID). The private PEM is generated on the production
# host and copied into the image; the public key is safe to expose to clients.
WEBPUSH_VAPID_PRIVATE_KEY = config(
    "WEBPUSH_VAPID_PRIVATE_KEY",
    default=str(BASE_DIR / "vapid_private.pem"),
)
WEBPUSH_VAPID_PUBLIC_KEY = config(
    "WEBPUSH_VAPID_PUBLIC_KEY",
    default="BNQgOkoLqdzGpYSThs4Na1IvfOHd2LU0ElkDhNPA86Ba-b2dXrcmHxIcGdcUeZ8OUhWJE6qqApPmrtdNaIpdIgk",
)
WEBPUSH_VAPID_SUBJECT = config("WEBPUSH_VAPID_SUBJECT", default="mailto:info@aspectcoffee.ru")
CKEDITOR_UPLOAD_PATH = "uploads/"
CKEDITOR_ALLOW_NONIMAGE_FILES = False
CKEDITOR_IMAGE_BACKEND = "pillow"
CKEDITOR_CONFIGS = {
    "default": {
        "toolbar": "Custom",
        "toolbar_Custom": [
            ["Bold", "Italic", "Underline", "Strike"],
            ["NumberedList", "BulletedList"],
            ["Link", "Unlink"],
            ["Image", "Table"],
            ["Source"],
        ],
        "height": 400,
        "width": "100%",
        "removePlugins": "stylesheetparser",
    }
}
YOOKASSA_SHOP_ID = config("YOOKASSA_SHOP_ID", default="")
YOOKASSA_SECRET_KEY = config("YOOKASSA_SECRET_KEY", default="")
CDEK_CLIENT_ID = config("CDEK_CLIENT_ID", default="")
CDEK_CLIENT_SECRET = config("CDEK_CLIENT_SECRET", default="")
CDEK_API_URL = config("CDEK_API_URL", default="https://api.cdek.ru/v2")
SENTRY_DSN = config("SENTRY_DSN", default="")
import sentry_sdk
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        traces_sample_rate=0.1,
        profiles_sample_rate=0.1,
        environment=config("ENVIRONMENT", default="development"),
    )
UNFOLD = {
    "SITE_TITLE": "Aspect Coffee",
    "SITE_HEADER": "Aspect Coffee — админ-панель",
    "SITE_URL": "/",
    "SITE_SYMBOL": "coffee",
    "DISABLE_DARK_MODE": True,
    "SITE_LOGO": {
        "light": lambda request: f"{STATIC_URL}asset/images/ic-logo-60.svg",
        "dark": lambda request: f"{STATIC_URL}asset/images/ic-logo-60.svg",
    },
    "SITE_FAVICONS": [
        {
            "href": lambda request: f"{STATIC_URL}asset/images/favicon.svg",
            "rel": "icon",
            "type": "image/svg+xml",
        },
    ],
    "STYLES": [
        lambda request: f"{STATIC_URL}css/unfold_aspect.css",
    ],
    "SCRIPTS": [
        lambda request: f"{STATIC_URL}asset/js/admin_ru.js?v=20260722-2",
    ],
    "LOGIN": {
        "image": lambda request: f"{STATIC_URL}images/bg-video-preview-1.jpg",
        "redirect_after": lambda request: "/admin/",
    },
    "COLORS": {
        "primary": {
            "50": "250 251 252",
            "100": "240 242 245",
            "200": "224 224 224",
            "300": "212 212 212",
            "400": "163 163 163",
            "500": "115 115 115",
            "600": "90 90 90",
            "700": "64 64 64",
            "800": "38 38 38",
            "900": "17 17 17",
            "950": "10 10 10",
        },
        "accent": {
            "50": "250 250 250",
            "100": "245 245 245",
            "200": "229 229 229",
            "300": "212 212 212",
            "400": "163 163 163",
            "500": "115 115 115",
            "600": "82 82 82",
            "700": "64 64 64",
            "800": "38 38 38",
            "900": "23 23 23",
            "950": "10 10 10",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": True,
        "navigation": [
            {
                "title": _("Каталог"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Категории"),
                        "icon": "category",
                        "link": reverse_lazy("admin:catalog_category_changelist"),
                    },
                    {
                        "title": _("Товары"),
                        "icon": "inventory_2",
                        "link": reverse_lazy("admin:catalog_product_changelist"),
                    },
                    {
                        "title": _("Обжарщики"),
                        "icon": "factory",
                        "link": reverse_lazy("admin:catalog_roaster_changelist"),
                    },
                    {
                        "title": _("Рецепты"),
                        "icon": "menu_book",
                        "link": reverse_lazy("admin:catalog_recipe_changelist"),
                    },
                    {
                        "title": _("Отзывы"),
                        "icon": "rate_review",
                        "link": reverse_lazy("admin:catalog_review_changelist"),
                    },
                    {
                        "title": _("Теги и фильтры"),
                        "icon": "sell",
                        "link": reverse_lazy("admin:catalog_tag_changelist"),
                    },
                    {
                        "title": _("Способы приготовления"),
                        "icon": "coffee",
                        "link": reverse_lazy("admin:catalog_brewmethod_changelist"),
                    },
                    {
                        "title": _("Виды помола"),
                        "icon": "grain",
                        "link": reverse_lazy("admin:catalog_grindtype_changelist"),
                    },
                    {
                        "title": _("Виды обжарки"),
                        "icon": "local_fire_department",
                        "link": reverse_lazy("admin:catalog_roasttype_changelist"),
                    },
                    {
                        "title": _("Упаковки"),
                        "icon": "package_2",
                        "link": reverse_lazy("admin:catalog_productpackaging_changelist"),
                    },
                    {
                        "title": _("Кофейни"),
                        "icon": "storefront",
                        "link": reverse_lazy("admin:catalog_cafe_changelist"),
                    },
                    {
                        "title": _("Главное меню"),
                        "icon": "menu",
                        "link": reverse_lazy("admin:catalog_navmenuitem_changelist"),
                    },
                    {
                        "title": _("Промо-слайды"),
                        "icon": "view_carousel",
                        "link": reverse_lazy("admin:catalog_promoslide_changelist"),
                    },
                    {
                        "title": _("Настройки сайта"),
                        "icon": "tune",
                        "link": reverse_lazy("admin:catalog_sitesettings_changelist"),
                    },
                    {
                        "title": _("Настройки фильтра"),
                        "icon": "filter_alt",
                        "link": reverse_lazy("admin:catalog_catalogfiltersettings_changelist"),
                    },
                    {
                        "title": _("Логи парсера"),
                        "icon": "history",
                        "link": reverse_lazy("admin:catalog_parserlog_changelist"),
                    },
                    {
                        "title": _("Настройки парсера"),
                        "icon": "settings",
                        "link": reverse_lazy("admin:catalog_parsersetting_changelist"),
                    },
                ],
            },
            {
                "title": _("Журнал"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Статьи"),
                        "icon": "article",
                        "link": reverse_lazy("admin:blog_blogpost_changelist"),
                    },
                    {
                        "title": _("Серии статей"),
                        "icon": "layers",
                        "link": reverse_lazy("admin:blog_blogseries_changelist"),
                    },
                    {
                        "title": _("Категории журнала"),
                        "icon": "topic",
                        "link": reverse_lazy("admin:blog_blogcategory_changelist"),
                    },
                    {
                        "title": _("Комментарии к статьям"),
                        "icon": "comment",
                        "link": reverse_lazy("admin:blog_articlecomment_changelist"),
                    },
                ],
            },
            {
                "title": _("Заказы и клиенты"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Заказы"),
                        "icon": "shopping_cart",
                        "link": reverse_lazy("admin:orders_order_changelist"),
                    },
                    {
                        "title": _("Корзины"),
                        "icon": "shopping_bag",
                        "link": reverse_lazy("admin:orders_cart_changelist"),
                    },
                    {
                        "title": _("Избранное"),
                        "icon": "favorite",
                        "link": reverse_lazy("admin:orders_wishlist_changelist"),
                    },
                    {
                        "title": _("Промо-коды"),
                        "icon": "local_offer",
                        "link": reverse_lazy("admin:orders_promocode_changelist"),
                    },
                    {
                        "title": _("Баннеры"),
                        "icon": "image",
                        "link": reverse_lazy("admin:orders_banner_changelist"),
                    },
                    {
                        "title": _("Пользователи"),
                        "icon": "person",
                        "link": reverse_lazy("admin:users_user_changelist"),
                    },
                    {
                        "title": _("Адреса"),
                        "icon": "location_on",
                        "link": reverse_lazy("admin:users_address_changelist"),
                    },
                    {
                        "title": _("Заметки к товарам"),
                        "icon": "note_alt",
                        "link": reverse_lazy("admin:orders_productnote_changelist"),
                    },
                ],
            },
            {
                "title": _("Сайт и сообщество"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Юридические документы"),
                        "icon": "gavel",
                        "link": reverse_lazy("admin:pages_legaldocument_changelist"),
                    },
                    {
                        "title": _("Ссылки сайта"),
                        "icon": "link",
                        "link": reverse_lazy("admin:pages_sitelink_changelist"),
                    },
                    {
                        "title": _("Баннеры страниц"),
                        "icon": "imagesmode",
                        "link": reverse_lazy("admin:pages_banner_changelist"),
                    },
                    {
                        "title": _("Публикации сообщества"),
                        "icon": "forum",
                        "link": reverse_lazy("admin:pages_communitypost_changelist"),
                    },
                    {
                        "title": _("Комментарии сообщества"),
                        "icon": "chat",
                        "link": reverse_lazy("admin:pages_communitypostcomment_changelist"),
                    },
                    {
                        "title": _("Комментарии к отзывам"),
                        "icon": "reviews",
                        "link": reverse_lazy("admin:pages_reviewcomment_changelist"),
                    },
                ],
            },
            {
                "title": _("Оплата, склад и уведомления"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Оплаты заказов"),
                        "icon": "payments",
                        "link": reverse_lazy("admin:payments_payment_changelist"),
                    },
                    {
                        "title": _("Автоповторы заказов"),
                        "icon": "autorenew",
                        "link": reverse_lazy("admin:orders_recurringorder_changelist"),
                    },
                    {
                        "title": _("История автосписаний"),
                        "icon": "receipt_long",
                        "link": reverse_lazy("admin:orders_recurringcharge_changelist"),
                    },
                    {
                        "title": _("Пополнения баланса"),
                        "icon": "account_balance_wallet",
                        "link": reverse_lazy("admin:users_paymenttransaction_changelist"),
                    },
                    {
                        "title": _("Остатки на складе"),
                        "icon": "warehouse",
                        "link": reverse_lazy("admin:warehouse_stockitem_changelist"),
                    },
                    {
                        "title": _("Логи email"),
                        "icon": "mail",
                        "link": reverse_lazy("admin:users_emaillog_changelist"),
                    },
                    {
                        "title": _("Уведомления пользователей"),
                        "icon": "notifications",
                        "link": reverse_lazy("admin:users_usernotification_changelist"),
                    },
                    {
                        "title": _("Push-подписки"),
                        "icon": "notifications_active",
                        "link": reverse_lazy("admin:users_pushsubscription_changelist"),
                    },
                    {
                        "title": _("Бонусные операции"),
                        "icon": "loyalty",
                        "link": reverse_lazy("admin:users_bonustransaction_changelist"),
                    },
                    {
                        "title": _("Уровни скидок"),
                        "icon": "percent",
                        "link": reverse_lazy("admin:users_discountlevel_changelist"),
                    },
                ],
            },
        ],
    },
}
CELERY_BEAT_SCHEDULE = {
    "sync-pending-yookassa-payments": {
        "task": "apps.payments.tasks.sync_pending_payments",
        "schedule": 60,
    },
    "process-due-recurring-orders": {
        "task": "apps.payments.tasks.process_due_recurring_orders",
        "schedule": 300,
    },
    "check-cdek-tracking": {
        "task": "apps.orders.tasks.check_cdek_tracking",
        "schedule": 3600,
    },
    "update-product-ratings": {
        "task": "apps.orders.tasks.update_product_ratings",
        "schedule": 86400,
    },
    "catalog-parser-sync": {
        "task": "apps.catalog.tasks.run_catalog_parser_task",
        "schedule": 86400, # Once a day
    },
    "check-product-images": {
        "task": "apps.catalog.tasks.check_product_images",
        "schedule": 86400, # Once a day — verify images exist on disk
    },
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ЮKassa Configuration
YOOKASSA_SHOP_ID = config("YOOKASSA_SHOP_ID", default="")
YOOKASSA_SECRET_KEY = config("YOOKASSA_SECRET_KEY", default="")
YOOKASSA_RECURRENT_ENABLED = config("YOOKASSA_RECURRENT_ENABLED", default=True, cast=bool)

# CDEK Configuration
CDEK_ACCOUNT = config("CDEK_CLIENT_ID", default="")
CDEK_PASSWORD = config("CDEK_CLIENT_SECRET", default="")
CDEK_TEST_MODE = config("CDEK_TEST_MODE", default=False, cast=bool)
