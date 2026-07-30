class GuestCartSessionMiddleware:
    """Save the pre-auth session key so cart merge works after login.

    Django's login() cycles the session key, so the guest cart stored
    under the old key can't be found by the user_logged_in signal.
    We stash the old key before AuthenticationMiddleware touches it.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if hasattr(request, "session"):
            if not request.session.session_key:
                request.session.create()
            if request.session.session_key:
                request._guest_session_key = request.session.session_key
        return self.get_response(request)
