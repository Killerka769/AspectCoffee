import json

from .phone_countries import PHONE_COUNTRIES


def phone_countries(request):
    """Expose the canonical phone configuration to every rendered page."""
    return {
        "phone_countries_json": json.dumps(
            PHONE_COUNTRIES,
            ensure_ascii=False,
            separators=(",", ":"),
        )
    }

