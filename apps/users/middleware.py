from django.shortcuts import redirect
from django.urls import reverse


class OAuthPhoneCompletionMiddleware:
    """Require OAuth users to finish a missing phone before using the site."""

    allowed_paths = {
        "/logout/",
        "/service-worker.js",
    }
    allowed_prefixes = (
        "/account/complete-phone/",
        "/accounts/",
        "/api/",
        "/static/",
        "/media/",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if (
            user
            and user.is_authenticated
            and not user.is_staff
            and (not user.phone or not user.phone_confirmed)
            and request.path not in self.allowed_paths
            and not request.path.startswith(self.allowed_prefixes)
            and user.socialaccount_set.exists()
        ):
            if request.method == "GET" and request.path.startswith("/"):
                request.session["phone_completion_next"] = request.get_full_path()
            return redirect(reverse("users:complete_phone"))
        return self.get_response(request)
