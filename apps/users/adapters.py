from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.core.exceptions import ImmediateHttpResponse
from django.core.files.base import ContentFile
from django.http import HttpResponseForbidden
from urllib.parse import quote
import logging
import requests

from .phone_confirmation import normalize_phone, phone_owner, phones_equal


logger = logging.getLogger(__name__)


class CustomAccountAdapter(DefaultAccountAdapter):
    """Custom account adapter: email-based auth, no usernames."""

    def is_open_for_signup(self, request):
        return True

    def clean_username(self, username, **kwargs):
        return None

    def save_user(self, request, user, form, commit=True):
        user = super().save_user(request, user, form, commit=False)
        from apps.users.models import User
        user.role = User.ROLE_CUSTOMER
        if commit:
            user.save()
        return user

    def send_account_already_exists_mail(self, email):
        # allauth's default builds this link via reverse("account_reset_password"),
        # which is allauth's own /accounts/password/reset/ URL (kept only as a
        # redirect to our real password-reset flow, see config/urls.py). reverse()
        # returns that route's own path, not its redirect target, so the emailed
        # link pointed at the deprecated URL instead of /password-reset/. Build
        # the link from our actual URL name instead.
        from django.urls import reverse
        from allauth.account.internal.flows import signup as signup_flows
        from allauth.core import context

        request = context.request
        password_reset_url = request.build_absolute_uri(reverse('password_reset'))
        signup_url = signup_flows.get_signup_url(request)
        ctx = {
            'request': request,
            'signup_url': signup_url,
            'password_reset_url': password_reset_url,
        }
        self.send_mail('account/email/account_already_exists', email, ctx)


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Custom social account adapter.
    Security fix: only connect to existing user if provider has
    verified the email address. Prevents account hijacking via
    unverified social emails.

    Enhanced to extract phone, first_name, last_name, and city from OAuth data.
    """

    def pre_social_login(self, request, sociallogin):
        if sociallogin.is_existing:
            self._sync_social_phone(
                sociallogin.user,
                sociallogin.account.provider,
                sociallogin.account.extra_data,
            )
            self._sync_yandex_avatar(
                sociallogin.user,
                sociallogin.account.extra_data,
            )
            return

        # Providers don't agree on where the email lives in extra_data:
        # Yandex only exposes "default_email"/"emails", not a plain
        # "email" key, so reading extra_data["email"] directly silently
        # found nothing and skipped all the logic below. sociallogin's own
        # email_addresses (populated by each provider's
        # extract_email_addresses()) is the provider-agnostic source of
        # truth; fall back to extra_data for providers (like VK) that
        # don't populate it.
        email = ""
        if sociallogin.email_addresses:
            email = sociallogin.email_addresses[0].email
        if not email:
            email = (
                sociallogin.account.extra_data.get("email", "")
                or sociallogin.account.extra_data.get("default_email", "")
            )
        if not email:
            return

        email_verified = sociallogin.account.extra_data.get("email_verified", False)
        provider = sociallogin.account.provider

        # VK treats any email as verified
        if provider == "vk":
            email_verified = bool(email)

        # Yandex OAuth always provides verified emails
        if provider == "yandex":
            email_verified = True

        if not email_verified:
            raise ImmediateHttpResponse(
                HttpResponseForbidden(
                    "Email адрес не подтверждён вашим провайдером. "
                    "Войдите через другой метод или подтвердите email."
                )
            )

        from apps.users.models import User
        try:
            existing_user = User.objects.get(email=email)
            sociallogin.connect(request, existing_user)
            # Provider already vouched for this email (checked above), so
            # mark it confirmed in our own email_confirmed flag too.
            if not existing_user.email_confirmed:
                existing_user.email_confirmed = True
                existing_user.save(update_fields=['email_confirmed'])
            self._sync_social_phone(existing_user, provider, sociallogin.account.extra_data)
            self._sync_yandex_avatar(
                existing_user,
                sociallogin.account.extra_data,
            )
        except User.DoesNotExist:
            pass

    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)
        from apps.users.models import User

        extra_data = sociallogin.account.extra_data
        provider = sociallogin.account.provider

        # Extract first_name and last_name
        if extra_data.get('first_name'):
            user.first_name = extra_data['first_name']
        if extra_data.get('last_name'):
            user.last_name = extra_data['last_name']

        phone = self._extract_phone(provider, extra_data)
        if phone and not phone_owner(phone):
            user.phone = phone
            user.phone_confirmed = True

        if provider == "yandex":
            self._sync_yandex_avatar(user, extra_data)

        # Extract city (if available from provider)
        if extra_data.get('city'):
            city_data = extra_data.get('city')
            if isinstance(city_data, dict):
                user.city = city_data.get('name', '')
            else:
                user.city = str(city_data)

        user.role = User.ROLE_CUSTOMER
        # OAuth provider already verified this email (pre_social_login
        # rejects unverified provider emails), so treat it as confirmed
        # in our own email_confirmed flag too, otherwise OAuth users get
        # permanently blocked at checkout by the email-confirmation gate.
        user.email_confirmed = True
        return user

    def _sync_yandex_avatar(self, user, extra_data):
        """Download a non-placeholder Yandex avatar once, without replacing uploads.

        Yandex ID returns ``default_avatar_id`` only when the OAuth application
        has requested the ``login:avatar`` permission. The avatar endpoint is
        public for that ID, so we persist a copy in our own media storage and
        do not depend on a remote URL when rendering the profile later.
        """
        if user.avatar or extra_data.get("is_avatar_empty"):
            return

        avatar_id = extra_data.get("default_avatar_id") or extra_data.get("avatar_id")
        if not avatar_id:
            return

        avatar_url = "https://avatars.yandex.net/get-yapic/{}/islands-200".format(
            quote(str(avatar_id), safe="/")
        )
        try:
            response = requests.get(avatar_url, timeout=8)
            response.raise_for_status()
            if not response.headers.get("Content-Type", "").startswith("image/"):
                return
            # A 200px Yandex portrait is far below the profile upload limit.
            if len(response.content) > 2 * 1024 * 1024:
                return
            user.avatar.save(
                "yandex-avatar.jpg",
                ContentFile(response.content),
                save=bool(user.pk),
            )
        except requests.RequestException:
            # A temporary avatar CDN failure must never block OAuth sign-in.
            logger.warning("Could not download the Yandex avatar for user %s", user.pk)

    def _extract_phone(self, provider, extra_data):
        phone = ""
        if provider == "yandex":
            # Yandex returns phone in format: {"number": "+79991234567"}.
            default_phone = extra_data.get("default_phone")
            if isinstance(default_phone, dict):
                phone = default_phone.get("number", "")
        elif provider == "vk":
            phone = extra_data.get("phone", "")
        return normalize_phone(phone)

    def _sync_social_phone(self, user, provider, extra_data):
        """Persist a provider-verified phone without creating duplicates."""
        provider_phone = self._extract_phone(provider, extra_data)
        if not provider_phone:
            return

        if user.phone and not phones_equal(user.phone, provider_phone):
            return
        if phone_owner(provider_phone, exclude_user_id=user.pk):
            return

        changed_fields = []
        if not user.phone:
            user.phone = provider_phone
            changed_fields.append("phone")
        if not user.phone_confirmed:
            user.phone_confirmed = True
            changed_fields.append("phone_confirmed")
        if changed_fields and user.pk:
            user.save(update_fields=changed_fields)
