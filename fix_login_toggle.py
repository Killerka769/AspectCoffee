import os

path = '/app/apps/users/views.py'
with open(path, 'r') as f:
    content = f.read()

old = """        if not user.email_confirmed:
            request.session["verify_email"] = email
            send_verification_email(user, request=request)
            messages.error(request, "Подтвердите email перед входом. Код отправлен на почту.")
            return redirect("users:verify_email")"""

new = """        from apps.users.verification import is_email_confirmation_enabled
        if is_email_confirmation_enabled() and not user.email_confirmed:
            request.session["verify_email"] = email
            send_verification_email(user, request=request)
            messages.error(request, "Подтвердите email перед входом. Код отправлен на почту.")
            return redirect("users:verify_email")"""

if old in content:
    content = content.replace(old, new)
    with open(path, 'w') as f:
        f.write(content)
    print("OK - login view updated")
else:
    print("ERROR: login block not found")
