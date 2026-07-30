"""Canonical phone handling shared by OAuth, profile and checkout flows."""

import re

from .phone_countries import PHONE_COUNTRIES, phone_country


def phone_digits(value):
    return re.sub(r"\D", "", value or "")


def normalize_phone(value, country_code=""):
    """Return a validated E.164-like phone value or an empty string."""
    raw = (value or "").strip()
    code_digits = phone_digits(country_code)
    digits = phone_digits(raw)

    selected_country = phone_country(country_code)
    if selected_country:
        # Forms submit the national part separately from the selected prefix.
        if raw.startswith("+") and digits.startswith(code_digits):
            local_digits = digits[len(code_digits):]
        elif digits.startswith(code_digits) and len(digits) > selected_country["length"]:
            local_digits = digits[len(code_digits):]
        elif country_code == "+7" and len(digits) == 11 and digits.startswith("8"):
            local_digits = digits[1:]
        else:
            local_digits = digits

        if len(local_digits) != selected_country["length"]:
            return ""
        return f"{country_code}{local_digits}"

    if raw.startswith("+"):
        # OAuth providers may return a complete number without a separate code.
        for country in sorted(
            PHONE_COUNTRIES,
            key=lambda item: len(phone_digits(item["code"])),
            reverse=True,
        ):
            prefix = phone_digits(country["code"])
            if digits.startswith(prefix):
                local_digits = digits[len(prefix):]
                if len(local_digits) != country["length"]:
                    return ""
                return f"{country['code']}{local_digits}"
        normalized_digits = digits
    elif code_digits:
        normalized_digits = (
            digits if digits.startswith(code_digits) else f"{code_digits}{digits}"
        )
    elif len(digits) == 11 and digits.startswith("8"):
        normalized_digits = f"7{digits[1:]}"
    elif digits:
        normalized_digits = digits
    else:
        return ""

    if not 8 <= len(normalized_digits) <= 15:
        return ""
    return f"+{normalized_digits}"


def phones_equal(left, right):
    left_digits = phone_digits(left)
    right_digits = phone_digits(right)
    return bool(left_digits and left_digits == right_digits)


def phone_owner(phone, *, exclude_user_id=None):
    """Find an existing owner without relying on historical formatting."""
    from apps.users.models import User

    normalized_digits = phone_digits(phone)
    if not normalized_digits:
        return None

    users = User.objects.exclude(phone="").only("pk", "email", "phone")
    if exclude_user_id:
        users = users.exclude(pk=exclude_user_id)
    for user in users:
        if phone_digits(user.phone) == normalized_digits:
            return user
    return None
