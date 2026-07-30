import os

path = '/app/apps/users/views.py'
with open(path, 'r') as f:
    content = f.read()

old = """def _resend_response(request, sent):
    if request.headers.get("HX-Request"):
        return render(request, "users/partials/resend_verification_status.html", {"sent": sent})
    return redirect("users:profile")"""

new = """def _resend_response(request, sent):
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        from django.http import JsonResponse
        return JsonResponse({"sent": sent})
    if request.headers.get("HX-Request"):
        return render(request, "users/partials/resend_verification_status.html", {"sent": sent})
    return redirect("users:verify_email")"""

if old in content:
    content = content.replace(old, new)
    with open(path, 'w') as f:
        f.write(content)
    print("OK - _resend_response returns JSON for AJAX")
else:
    print("ERROR: _resend_response not found")
