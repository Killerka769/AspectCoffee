"""Email verification helpers - OTP code version."""
from __future__ import annotations
import logging
import random
import string
from typing import Optional, Tuple
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.core.cache import cache
from django.template.loader import render_to_string
from .models import EmailLog

logger = logging.getLogger(__name__)
User = get_user_model()
CODE_LENGTH = 6
CODE_TTL_SECONDS = 900
RESEND_COOLDOWN_SECONDS = 60

def generate_otp_code():
    return "".join(random.choices(string.digits, k=CODE_LENGTH))

def save_otp_code(user):
    code = generate_otp_code()
    key = f"email_verify_{user.pk}"
    cache.set(key, code, CODE_TTL_SECONDS)
    return code

def verify_otp_code(user, code):
    key = f"email_verify_{user.pk}"
    stored = cache.get(key)
    if stored is None:
        return False, "Code expired"
    if stored != code.strip():
        return False, "Wrong code"
    cache.delete(key)
    return True, None

def send_verification_email(user, request=None):
    code = save_otp_code(user)
    subject = "Код подтверждения — Aspect Coffee"
    name = user.first_name or user.email
    text_body = f"Здравствуйте, {name}!\n\nВаш код подтверждения: {code}\n\nКод действителен 15 минут.\n\nЕсли вы не регистрировались, просто проигнорируйте это письмо.\n\nС уважением,\nкоманда Aspect Coffee"
    html_body = render_to_string(
        "users/emails/verify_email.html",
        {"user": user, "code": code, "site_name": "Aspect Coffee"},
    )
    success = False
    error_message = ""
    try:
        sent = send_mail(
            subject=subject,
            message=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_body,
            fail_silently=False,
        )
        success = bool(sent)
    except Exception as exc:
        error_message = str(exc)
    EmailLog.objects.create(
        recipient=user.email, subject=subject, body=text_body,
        success=success, error_message=error_message,
    )
    return success


def is_email_confirmation_enabled():
    """Feature flag: require email (OTP) confirmation before login.

    Referenced by login_view / register but was never defined, which raised
    ImportError -> HTTP 500 on valid login and on registration completion.
    Reads settings.EMAIL_CONFIRMATION_ENABLED, defaulting to False so existing
    accounts (email_confirmed=False) are not locked out and the previous
    working login/register behaviour is restored. Toggle to True (via env)
    to enable the OTP flow.
    """
    from django.conf import settings
    return getattr(settings, "EMAIL_CONFIRMATION_ENABLED", False)


# --- Account-unlock-via-email (django-axes lockout self-service) ---

UNLOCK_CODE_TTL_SECONDS = 600  # 10 minutes
UNLOCK_RESEND_COOLDOWN_SECONDS = 60


def _unlock_cache_key(email):
    return f"unlock_account_{email.lower().strip()}"


def save_unlock_code(email):
    """Generate and cache a 6-digit unlock code for the given email (not tied to a User pk,
    since a locked-out request may not resolve to a real user yet — avoids user enumeration
    by always succeeding the same way regardless of whether the email exists)."""
    code = generate_otp_code()
    cache.set(_unlock_cache_key(email), code, UNLOCK_CODE_TTL_SECONDS)
    return code


def verify_unlock_code(email, code):
    key = _unlock_cache_key(email)
    stored = cache.get(key)
    if stored is None:
        return False, "Код истёк или не был запрошен"
    if stored != code.strip():
        return False, "Неверный код"
    cache.delete(key)
    return True, None


def send_unlock_email(user, request=None):
    """Send the account-unlock code to user.email. Mirrors send_verification_email but
    uses a separate cache namespace/TTL and copy so it can't be confused with the
    registration/login email-confirmation OTP flow."""
    code = save_unlock_code(user.email)
    subject = "Код разблокировки аккаунта — Aspect Coffee"
    name = user.first_name or user.email
    text_body = (
        f"Здравствуйте, {name}!\n\n"
        f"Кто-то (возможно, вы) несколько раз неудачно пытался войти в ваш аккаунт, "
        f"поэтому вход временно заблокирован.\n\n"
        f"Код разблокировки: {code}\n\n"
        f"Код действителен 10 минут.\n\n"
        f"Если это были не вы, рекомендуем сменить пароль после входа.\n\n"
        f"С уважением,\nкоманда Aspect Coffee"
    )
    html_body = render_to_string(
        "users/emails/unlock_account.html",
        {"user": user, "code": code, "site_name": "Aspect Coffee"},
    )
    success = False
    error_message = ""
    try:
        sent = send_mail(
            subject=subject,
            message=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_body,
            fail_silently=False,
        )
        success = bool(sent)
    except Exception as exc:
        error_message = str(exc)
    EmailLog.objects.create(
        recipient=user.email, subject=subject, body=text_body,
        success=success, error_message=error_message,
    )
    return success
