import base64
import hashlib
import json
import secrets
from datetime import timedelta
from urllib.parse import urlencode

import requests
from allauth.account.internal.decorators import login_not_required
from allauth.socialaccount.adapter import get_adapter
from allauth.socialaccount.helpers import complete_social_login
from allauth.socialaccount.models import SocialToken
from allauth.socialaccount.providers.oauth2.views import (
    OAuth2CallbackView,
)
from allauth.socialaccount.providers.yandex.views import YandexOAuth2Adapter
from django.contrib import messages
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme


VKID_AUTHORIZE_URL = "https://id.vk.ru/authorize"
VKID_TOKEN_URL = "https://id.vk.ru/oauth2/auth"
VKID_USER_INFO_URL = "https://id.vk.ru/oauth2/user_info"
VKID_SDK_VERSION = "2.6.6"


class RussianYandexOAuth2Adapter(YandexOAuth2Adapter):
    """Use Yandex's Russian OAuth host instead of the default .com host."""

    authorize_url = "https://oauth.yandex.ru/authorize"


yandex_oauth_callback = OAuth2CallbackView.adapter_view(RussianYandexOAuth2Adapter)


@login_not_required
def yandex_oauth_login(request):
    """Start Yandex OAuth with the Russian authorization host."""
    provider = get_adapter(request).get_provider(request, provider="yandex")
    provider.oauth2_adapter_class = RussianYandexOAuth2Adapter
    return provider.redirect_from_request(request)


def _safe_next_url(request, value):
    if value and url_has_allowed_host_and_scheme(
        value,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return value
    return "/account/profile/"


def _vkid_callback_url(request):
    return request.build_absolute_uri("/accounts/vk/login/callback/")


def vkid_login(request):
    """Start the current VK ID OAuth 2.1 + PKCE flow."""
    provider = get_adapter(request).get_provider(request, provider="vk")
    app_id = int(provider.app.client_id)
    state = secrets.token_urlsafe(32)
    code_verifier = secrets.token_urlsafe(64)
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode("ascii")).digest()
    ).rstrip(b"=").decode("ascii")
    stats_info = base64.b64encode(json.dumps(
        {
            "flow_source": "from_custom_auth",
            "session_id": secrets.token_urlsafe(16),
        },
        separators=(",", ":"),
    ).encode("utf-8")).decode("ascii")

    request.session["vkid_oauth_state"] = state
    request.session["vkid_code_verifier"] = code_verifier
    request.session["vkid_next"] = _safe_next_url(request, request.GET.get("next"))

    params = {
        "lang_id": 0,
        "code_challenge": code_challenge,
        "code_challenge_method": "s256",
        "client_id": app_id,
        "response_type": "code",
        "scope": "phone email",
        "state": state,
        "prompt": "",
        "stats_info": stats_info,
        "v": VKID_SDK_VERSION,
        "sdk_type": "vkid",
        "app_id": app_id,
        "redirect_uri": _vkid_callback_url(request),
    }
    return redirect(f"{VKID_AUTHORIZE_URL}?{urlencode(params)}")


def vkid_callback(request):
    """Exchange the VK ID code, then hand the verified profile to allauth."""
    next_url = _safe_next_url(request, request.session.pop("vkid_next", ""))
    expected_state = request.session.pop("vkid_oauth_state", "")
    code_verifier = request.session.pop("vkid_code_verifier", "")
    state = request.GET.get("state", "")
    code = request.GET.get("code", "")
    device_id = request.GET.get("device_id", "")

    if (
        not expected_state
        or not state
        or not secrets.compare_digest(expected_state, state)
        or not code
        or not device_id
        or request.GET.get("error")
    ):
        messages.error(request, "Не удалось выполнить вход через VK ID. Попробуйте ещё раз.")
        return redirect(f"/login/?{urlencode({'next': next_url})}")

    provider = get_adapter(request).get_provider(request, provider="vk")
    app = provider.app
    app_id = int(app.client_id)
    token_params = {
        "grant_type": "authorization_code",
        "redirect_uri": _vkid_callback_url(request),
        "client_id": app_id,
        "code_verifier": code_verifier,
        "state": state,
        "device_id": device_id,
    }

    try:
        token_response = requests.post(
            VKID_TOKEN_URL,
            params=token_params,
            data={"code": code},
            timeout=15,
        )
        token_response.raise_for_status()
        token_data = token_response.json()
        if token_data.get("error"):
            raise ValueError(token_data.get("error_description") or token_data["error"])

        profile_response = requests.post(
            VKID_USER_INFO_URL,
            params={"client_id": app_id},
            data={"access_token": token_data["access_token"]},
            timeout=15,
        )
        profile_response.raise_for_status()
        profile_data = profile_response.json()
        if profile_data.get("error"):
            raise ValueError(profile_data.get("error_description") or profile_data["error"])
    except (KeyError, ValueError, requests.RequestException):
        messages.error(request, "VK ID временно недоступен. Попробуйте войти ещё раз.")
        return redirect(f"/login/?{urlencode({'next': next_url})}")

    extra_data = dict(profile_data.get("user") or {})
    extra_data["id"] = str(extra_data.pop("user_id", token_data.get("user_id", "")))
    extra_data["email_verified"] = bool(extra_data.get("email"))

    sociallogin = provider.sociallogin_from_response(request, extra_data)
    token = SocialToken(
        app=app,
        token=token_data["access_token"],
        token_secret=token_data.get("refresh_token", ""),
    )
    if token_data.get("expires_in"):
        token.expires_at = timezone.now() + timedelta(seconds=int(token_data["expires_in"]))
    sociallogin.token = token
    sociallogin.state = {"next": next_url, "process": "login"}
    return complete_social_login(request, sociallogin)
