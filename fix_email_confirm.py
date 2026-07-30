import os

# 1. Add toggle check function to verification.py
path = '/app/apps/users/verification.py'
with open(path, 'r') as f:
    content = f.read()

# Add function before send_verification_email
old_func = """def send_verification_email(user, request=None):"""

new_func = """def is_email_confirmation_enabled():
    from apps.catalog.models import SiteSettings
    return SiteSettings.load().email_confirmation_enabled


def send_verification_email(user, request=None):"""

if old_func in content:
    content = content.replace(old_func, new_func)
    with open(path, 'w') as f:
        f.write(content)
    print("OK - added is_email_confirmation_enabled()")
else:
    print("ERROR: send_verification_email not found")

# 2. Update register view to check toggle
reg_path = '/app/apps/users/views.py'
with open(reg_path, 'r') as f:
    content = f.read()

# Find the register view and add toggle check
old_register_send = """        try:
            send_verification_email(user, request=request)
        except Exception:
            pass
        return redirect("users:verify_email")"""

new_register_send = """        from apps.users.verification import is_email_confirmation_enabled
        if is_email_confirmation_enabled():
            try:
                send_verification_email(user, request=request)
            except Exception:
                pass
            return redirect("users:verify_email")
        else:
            user.email_confirmed = True
            user.save(update_fields=["email_confirmed"])
            from django.contrib.auth import login as auth_login
            auth_login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            return redirect("users:profile")"""

if old_register_send in content:
    content = content.replace(old_register_send, new_register_send)
    with open(reg_path, 'w') as f:
        f.write(content)
    print("OK - register view updated with toggle check")
else:
    print("ERROR: register send block not found")

# 3. Update login view to check toggle
old_login = """        if not user.email_confirmed:
            try:
                send_verification_email(user, request=request)
            except Exception:
                pass
            messages.warning(request, "Подтвердите email. Письмо отправлено повторно.")
            return redirect("users:verify_email")"""

new_login = """        from apps.users.verification import is_email_confirmation_enabled
        if is_email_confirmation_enabled() and not user.email_confirmed:
            try:
                send_verification_email(user, request=request)
            except Exception:
                pass
            messages.warning(request, "Подтвердите email. Письмо отправлено повторно.")
            return redirect("users:verify_email")"""

if old_login in content:
    content = content.replace(old_login, new_login)
    with open(reg_path, 'w') as f:
        f.write(content)
    print("OK - login view updated with toggle check")
else:
    print("ERROR: login block not found")

# 4. Fix resend_verification - remove @login_required, allow unauthenticated
old_resend = """@login_required
@require_POST
def resend_verification(request):
    user = request.user
    sent_ok = False
    if user.email_confirmed:
        messages.info(request, "Ваш email уже подтверждён.")
    else:"""

new_resend = """@require_POST
def resend_verification(request):
    user = None
    if request.user.is_authenticated:
        user = request.user
    else:
        email = request.session.get("verify_email")
        if email:
            from apps.users.models import User
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                pass
    if not user:
        messages.error(request, "Не удалось определить пользователя. Попробуйте войти или зарегистрироваться заново.")
        return redirect("users:register")
    sent_ok = False
    if user.email_confirmed:
        messages.info(request, "Ваш email уже подтверждён.")
    else:"""

if old_resend in content:
    content = content.replace(old_resend, new_resend)
    with open(reg_path, 'w') as f:
        f.write(content)
    print("OK - resend_verification: removed @login_required, supports unauthenticated")
else:
    print("ERROR: resend_verification block not found")

print("All done")
