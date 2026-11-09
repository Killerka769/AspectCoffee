
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView
from apps.users.forms import AspectCoffeePasswordResetForm
from apps.users.views import register, custom_logout, profile, wishlist_view, my_favorites_view, login_view, unlock_account, resend_unlock_code, service_worker, pwa_worker
from apps.users.oauth_views import (
    vkid_callback,
    vkid_login,
    yandex_oauth_callback,
    yandex_oauth_login,
)
from apps.api.views import RegisterView as ApiRegisterView

def api_register_redirect(request):
    """
    Agar /api/v1/auth/register/ ga brauzerdan ko'rish uchun kirilsa (GET),
    oddiy /register/ sahifasiga o'tkazib yuboriladi.
    Lekin API orqali ro'yxatdan o'tish (POST) ishlashda davom etadi.
    """
    if request.method == "GET":
        from django.shortcuts import redirect
        return redirect("/register/")
    return ApiRegisterView.as_view()(request)

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)
from rest_framework.permissions import IsAdminUser
from drf_spectacular.views import SpectacularAPIView
from apps.pages.views_webhook import webhook_deploy
urlpatterns = [
    path("service-worker.js", service_worker, name="service_worker"),
    path("sw.js", pwa_worker, name="pwa_worker"),
    path("admin/", admin.site.urls),
    path("", include("apps.catalog.urls", namespace="catalog")),
    path("account/", include("apps.users.urls", namespace="users")),
    path("", include("apps.orders.urls", namespace="orders")),
    path("ckeditor/", include("ckeditor_uploader.urls")),
    path("login/", login_view, name="login"),
    path("unlock-account/", unlock_account, name="unlock_account"),
    path("unlock-account/resend/", resend_unlock_code, name="resend_unlock_code"),
    path("register/", register, name="register"),
    path("create-account/", register, name="create_account"),
    path("logout/", custom_logout, name="logout"),
    path("profile/", RedirectView.as_view(url="/account/profile/", permanent=True), name="profile_redirect"),
    path("password-reset/", auth_views.PasswordResetView.as_view(template_name="users/password_reset.html", form_class=AspectCoffeePasswordResetForm), name="password_reset"),
    path("password-reset/done/", auth_views.PasswordResetDoneView.as_view(template_name="users/password_reset_done.html"), name="password_reset_done"),
    path("password-reset/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(template_name="users/password_reset_confirm.html"), name="password_reset_confirm"),
    path("password-reset/complete/", auth_views.PasswordResetCompleteView.as_view(template_name="users/password_reset_complete.html"), name="password_reset_complete"),
    # Redirect /admin/logout/ to our custom logout (avoid Django admin logout requiring POST)
    path("admin/logout/", custom_logout, name="admin_logout"),
    # /my-favorites → user wishlist
    path("my-favorites/", my_favorites_view, name="my_favorites"),
    # Category shortcut pages
    path("tea/", RedirectView.as_view(url="/catalog/?category=chay", permanent=False), name="tea"),
    path("accessories/", RedirectView.as_view(url="/catalog/?category=aksessuary", permanent=False), name="accessories"),
    path("chocolate/", RedirectView.as_view(url="/catalog/?category=chocolate", permanent=False), name="chocolate"),
    path("giftbox/", RedirectView.as_view(url="/catalog/?category=giftbox", permanent=False), name="giftbox"),
    path("accessories/gift-certificate/", RedirectView.as_view(url="/catalog/?category=gift-certificate", permanent=False), name="gift_certificate"),
    # Allauth ships its own parallel password-reset flow under accounts/
    # (account_reset_password etc.). Nothing in this app links to it, but
    # it is still publicly reachable and, if hit directly, sends users an
    # unstyled email pointing at /accounts/password/reset/ instead of our
    # custom, correctly-styled /password-reset/ flow. Redirect it here so
    # that flow is unreachable and only the custom one is ever used.
    path("accounts/password/reset/", RedirectView.as_view(pattern_name="password_reset", permanent=False), name="account_reset_password"),
    path("accounts/password/reset/done/", RedirectView.as_view(pattern_name="password_reset_done", permanent=False), name="account_reset_password_done"),
    # Override the provider routes before allauth's include:
    # VK now requires VK ID OAuth 2.1 + PKCE; Yandex's .ru host keeps the
    # authorization form in Russian.
    path("accounts/vk/login/", vkid_login, name="vk_login"),
    path("accounts/vk/login/callback/", vkid_callback, name="vk_callback"),
    path("accounts/yandex/login/", yandex_oauth_login, name="yandex_login"),
    path("accounts/yandex/login/callback/", yandex_oauth_callback, name="yandex_callback"),
    path("accounts/", include("allauth.urls")),
    # /help/loyalty/ → redirect to discount-system page
    path("help/loyalty/", RedirectView.as_view(url="/discount-system/", permanent=False), name="help_loyalty"),
    path("", include("apps.pages.urls", namespace="pages")),
    path("blog/", include("apps.blog.urls", namespace="blog")),
]
urlpatterns += [
    path(
        "api/v1/auth/register/",
        api_register_redirect,
        name="api_register",
    ),
    path("api/v1/", include("apps.api.urls")),
    path("api/v1/", include("apps.payments.urls")),
    path("api/cdek/", include("apps.delivery.urls", namespace="delivery")),
    path("warehouse/", include("apps.warehouse.urls", namespace="warehouse")),
]
urlpatterns += [
    path("api/schema/", SpectacularAPIView.as_view(permission_classes=[IsAdminUser]), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema", permission_classes=[IsAdminUser]), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema", permission_classes=[IsAdminUser]), name="redoc"),
    path("webhook/deploy/", webhook_deploy, name="webhook_deploy"),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    try:
        import debug_toolbar
        urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
    except ImportError:
        pass

# 1.4.7 — ЧПУ раздела/категории по иерархии из админки:
#   /coffee            -> раздел
#   /coffee/dlya-turki -> дочерняя категория
from apps.catalog.views import section_catalog  # noqa: E402
urlpatterns += [
    path("<slug:section>/", section_catalog, name="catalog_section"),
    path("<slug:section>/<slug:child>/", section_catalog, name="catalog_section_child"),
]

def custom_404(request, exception=None):
    from django.shortcuts import render
    return render(request, "404.html", status=404)


def custom_500(request):
    from django.http import HttpResponseServerError
    from django.template.loader import get_template
    return HttpResponseServerError(get_template("500.html").render({}))


handler404 = "config.urls.custom_404"
handler500 = "config.urls.custom_500"
