import re
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404, reverse
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Prefetch
from django.http import FileResponse, HttpResponse, HttpResponseForbidden, JsonResponse
from django.templatetags.static import static
import json
from urllib.parse import urlsplit
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from apps.orders.models import Order, OrderItem, Wishlist, Cart, CartItem, ProductNote
from apps.users.models import Address, EmailLog
from .verification import (
    send_verification_email,
    verify_otp_code,
    RESEND_COOLDOWN_SECONDS,
    send_unlock_email,
    verify_unlock_code,
    UNLOCK_RESEND_COOLDOWN_SECONDS,
)

@login_required
@never_cache
def complete_phone(request):
    """Finish an OAuth account when the provider did not return a phone."""
    from .phone_confirmation import normalize_phone, phone_owner

    providers = list(
        request.user.socialaccount_set.values_list("provider", flat=True).distinct()
    )
    provider_names = {
        "yandex": "Яндекс",
        "vk": "VK",
        "google": "Google",
    }
    provider_label = ", ".join(
        provider_names.get(provider, provider.title()) for provider in providers
    ) or "сервис авторизации"

    if request.user.phone and request.user.phone_confirmed:
        return redirect("users:profile")

    if request.method == "POST":
        phone_code = (request.POST.get("phone_code") or "+7").strip()
        phone = normalize_phone(request.POST.get("phone", ""), phone_code)
        repeated_phone = normalize_phone(request.POST.get("phone_repeat", ""), phone_code)

        if not phone:
            messages.error(request, "Укажите корректный номер телефона.")
        elif phone != repeated_phone:
            messages.error(request, "Номера не совпадают. Повторите ввод.")
        elif phone_owner(phone, exclude_user_id=request.user.pk):
            messages.error(
                request,
                "Этот номер уже используется другим аккаунтом. "
                "Войдите в соответствующую учётную запись или укажите другой номер.",
            )
        else:
            request.user.phone = phone
            request.user.phone_confirmed = True
            request.user.save(update_fields=["phone", "phone_confirmed"])
            messages.success(request, "Номер телефона подтверждён и сохранён.")
            next_url = request.session.pop("phone_completion_next", "")
            service_prefixes = (
                "/api/",
                "/accounts/",
                "/static/",
                "/media/",
                "/account/complete-phone/",
            )
            next_path = urlsplit(next_url).path
            if (
                not url_has_allowed_host_and_scheme(
                    next_url,
                    allowed_hosts={request.get_host()},
                    require_https=request.is_secure(),
                )
                or not next_path.startswith("/")
                or next_path.startswith(service_prefixes)
            ):
                next_url = reverse("users:profile")
            return redirect(next_url)

    return render(
        request,
        "users/complete_phone.html",
        {
            "provider_label": provider_label,
            "phone_code": request.POST.get("phone_code", "+7"),
            "phone_value": request.POST.get("phone", ""),
            "phone_repeat": request.POST.get("phone_repeat", ""),
        },
    )


@login_required
def profile(request):
    if request.method == "POST":
        from .phone_confirmation import normalize_phone, phone_owner

        user = request.user
        action = request.POST.get("action")

        if action == "avatar":
            if "avatar" in request.FILES:
                user.avatar = request.FILES["avatar"]
                user.save()
                messages.success(request, "Аватар обновлён")
            return redirect(request.POST.get("next", "users:profile"))

        # Standard profile update
        full_name = request.POST.get("full_name", "").strip()
        parts = full_name.split(None, 1)
        user.first_name = parts[0] if parts else ""
        user.last_name = parts[1] if len(parts) > 1 else ""
        phone_code = request.POST.get("phone_code", "").strip()
        submitted_phone = request.POST.get("phone", "").strip()
        normalized_phone = normalize_phone(submitted_phone, phone_code)
        if submitted_phone and not normalized_phone:
            messages.error(request, "Укажите корректный номер телефона")
            return redirect("users:profile")
        owner = phone_owner(normalized_phone, exclude_user_id=user.pk)
        if owner:
            messages.error(
                request,
                "Этот номер уже используется другой учётной записью",
            )
            return redirect("users:profile")
        user.phone = normalized_phone
        user.phone_confirmed = bool(normalized_phone)
        user.email = request.POST.get("email", user.email).strip() # Allow email update too
        user.company_name = request.POST.get("company_name", "").strip()
        user.company_inn = request.POST.get("company_inn", "").strip()
        user.company_kpp = request.POST.get("company_kpp", "").strip()
        user.company_address = request.POST.get("company_address", "").strip()
        user.save()
        messages.success(request, "Данные сохранены")
        return redirect("users:profile")

    addresses = request.user.addresses.all() if request.user.is_authenticated else []
    return render(request, "users/profile.html", {"section": "profile", "addresses": addresses})


@login_required
def change_password(request):
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    if request.method == "POST":
        current = request.POST.get("current_password", "")
        new = request.POST.get("new_password", "")
        new2 = request.POST.get("new_password2", "")
        if not request.user.check_password(current):
            if is_ajax:
                return JsonResponse({"error": "Текущий пароль неверен"}, status=400)
            messages.error(request, "Текущий пароль неверен")
        elif new != new2:
            if is_ajax:
                return JsonResponse({"error": "Новые пароли не совпадают"}, status=400)
            messages.error(request, "Новые пароли не совпадают")
        elif len(new) < 8:
            if is_ajax:
                return JsonResponse({"error": "Пароль должен быть не менее 8 символов"}, status=400)
            messages.error(request, "Пароль должен быть не менее 8 символов")
        else:
            request.user.set_password(new)
            request.user.save()
            update_session_auth_hash(request, request.user)
            if is_ajax:
                return JsonResponse({"ok": True, "message": "Пароль успешно изменён"})
            messages.success(request, "Пароль успешно изменён")
        if is_ajax:
            return JsonResponse({"error": "Ошибка"}, status=400)
        return redirect("users:profile")
    return render(request, "users/change_password.html")


@login_required
@require_POST
def delete_account(request):
    password = request.POST.get("password", "")
    if request.user.check_password(password):
        request.user.delete()
        messages.success(request, "Аккаунт удалён")
        return redirect("/")
    messages.error(request, "Неверный пароль")
    return redirect("users:profile")

@login_required
def orders_history(request):
    current_orders = Order.objects.filter(
        user=request.user,
        status__in=[Order.STATUS_NEW, Order.STATUS_PAID, Order.STATUS_ASSEMBLING, Order.STATUS_SHIPPED],
    ).select_related("payment").prefetch_related("items").order_by("-created_at")
    orders_qs = Order.objects.filter(user=request.user).select_related("payment").prefetch_related("items").order_by("-created_at")
    paginator = Paginator(orders_qs, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    return render(request, "users/orders.html", {
        "page_obj": page_obj,
        "orders": page_obj.object_list,
        "current_orders": current_orders,
        "section": "orders",
    })


@login_required
def order_detail(request, pk):
    order = get_object_or_404(
        Order.objects.prefetch_related("items__variant__product"),
        pk=pk, user=request.user,
    )
    recurring_plan = getattr(order, "recurring_plan", None)
    from apps.payments.services import order_payment_context

    return render(request, "users/order_detail.html", {
        "order": order,
        "recurring_plan": recurring_plan,
        "section": "orders",
        **order_payment_context(order),
    })


@login_required
@require_POST
def cancel_recurring_order(request, pk):
    from apps.orders.models import RecurringOrder

    plan = get_object_or_404(
        RecurringOrder,
        source_order_id=pk,
        user=request.user,
    )
    if plan.status != RecurringOrder.STATUS_CANCELLED:
        plan.status = RecurringOrder.STATUS_CANCELLED
        plan.next_charge_at = None
        plan.save(update_fields=["status", "next_charge_at", "updated_at"])
        messages.success(request, "Автоматическое повторение заказа отключено")
    return redirect("users:order_detail", pk=pk)


@login_required
@require_POST
def cancel_order(request, pk):
    order = get_object_or_404(Order, pk=pk, user=request.user)
    if order.status not in (Order.STATUS_NEW, Order.STATUS_PAID):
        messages.error(request, "Этот заказ нельзя отменить")
        return redirect("users:order_detail", pk=pk)
    order.status = Order.STATUS_CANCELLED
    order.save(update_fields=["status"])
    if order.payment_status == Order.PAYMENT_STATUS_PAID:
        from apps.payments.tasks import process_refund
        try:
            process_refund.delay(order.id)
            messages.success(request, f"Заказ #{pk} отменён. Возврат средств будет обработан в течение нескольких дней.")
        except Exception:
            messages.warning(request, f"Заказ #{pk} отменён. Для возврата средств свяжитесь с нами.")
    else:
        messages.success(request, f"Заказ #{pk} отменён")
    return redirect("users:orders")


@login_required
@require_POST
def reorder(request, pk):
    order = get_object_or_404(Order, pk=pk, user=request.user)
    from apps.orders.reorder import add_order_items_to_user_cart

    result = add_order_items_to_user_cart(order, request.user)
    added = result["added"]
    skipped = result["skipped"]
    if added:
        messages.success(request, f"Добавлено {added} позиций в корзину.")
    if skipped:
        messages.warning(request, f"Недоступны и пропущены: {', '.join(skipped)}")
    return redirect("orders:basket")


@login_required
def download_invoice(request, pk):
    order = get_object_or_404(Order, pk=pk, user=request.user)
    if not request.user.is_wholesale:
        return HttpResponseForbidden("Доступно только для оптовых покупателей")
    from apps.orders.utils import generate_wholesale_invoice_pdf
    buffer = generate_wholesale_invoice_pdf(order)
    return FileResponse(buffer, as_attachment=True, filename=f"invoice_{pk}.pdf", content_type="application/pdf")

@login_required
def wishlist_view(request):
    items = Wishlist.objects.filter(user=request.user).select_related("product").order_by("-added_at")
    notes = ProductNote.objects.filter(user=request.user).select_related("product").order_by("-updated_at")
    notes_dict = {n.product_id: n.text for n in notes}
    return render(request, "users/wishlist.html", {
        "wishlist_items": items,
        "product_notes": notes,
        "product_notes_dict": notes_dict,
        "section": "wishlist",
    })

def my_favorites_view(request):
    if request.user.is_authenticated:
        items = Wishlist.objects.filter(user=request.user).select_related("product").order_by("-added_at")
        notes = ProductNote.objects.filter(user=request.user).select_related("product").order_by("-updated_at")
        notes_dict = {n.product_id: n.text for n in notes}
    else:
        from types import SimpleNamespace
        from apps.catalog.models import Product
        ids_raw = request.GET.get("ids", "")
        ids = [int(x) for x in ids_raw.split(",") if x.strip().isdigit()]
        prod_map = {p.id: p for p in Product.objects.filter(id__in=ids)} if ids else {}
        items = [SimpleNamespace(product=prod_map[i]) for i in ids if i in prod_map]
        notes = []
        notes_dict = {}
    return render(request, "users/my_favorites.html", {
        "wishlist_items": items,
        "product_notes": notes,
        "product_notes_dict": notes_dict,
    })

def mini_wishlist(request):
    if not request.user.is_authenticated:
        return render(request, "users/partials/mini_wishlist.html", {"wishlist_items": [], "total": 0})
    items = Wishlist.objects.filter(user=request.user).select_related("product").order_by("-added_at")[:4]
    total = Wishlist.objects.filter(user=request.user).count()
    return render(request, "users/partials/mini_wishlist.html", {"wishlist_items": items, "total": total})

@login_required
def addresses_view(request):
    if request.method == "POST":
        addresses = request.user.addresses.all()
        action = request.POST.get("action")
        if action == "add":
            city = (request.POST.get("city") or "").strip()
            street = (request.POST.get("street") or "").strip()
            if not city or not street:
                messages.error(request, "Укажите город и улицу")
            else:
                make_default = (
                    request.POST.get("is_default") == "on"
                    or not request.user.addresses.exists()
                )
                if make_default:
                    Address.objects.filter(user=request.user).update(is_default=False)
                Address.objects.create(
                    user=request.user,
                    label=request.POST.get("label", ""),
                    city=city,
                    street=street,
                    house=request.POST.get("house", ""),
                    apartment=request.POST.get("apartment", ""),
                    postal_code=request.POST.get("postal_code", ""),
                    is_default=make_default,
                )
                messages.success(request, "Адрес добавлен")
        elif action == "edit":
            addr = get_object_or_404(Address, pk=request.POST.get("id"), user=request.user)
            city = (request.POST.get("city") or "").strip()
            street = (request.POST.get("street") or "").strip()
            if not city or not street:
                messages.error(request, "Укажите город и улицу")
            else:
                addr.label = request.POST.get("label", "")
                addr.city = city
                addr.street = street
                addr.house = request.POST.get("house", "")
                addr.apartment = request.POST.get("apartment", "")
                addr.postal_code = request.POST.get("postal_code", "")
                make_default = request.POST.get("is_default") == "on"
                if make_default and not addr.is_default:
                    Address.objects.filter(user=request.user).update(is_default=False)
                    addr.is_default = True
                addr.save()
                messages.success(request, "Адрес обновлён")
        elif action == "delete":
            addr = get_object_or_404(Address, pk=request.POST.get("id"), user=request.user)
            addr.delete()
            messages.success(request, "Адрес удалён")
        elif action == "set_default":
            Address.objects.filter(user=request.user).update(is_default=False)
            addr = get_object_or_404(Address, pk=request.POST.get("id"), user=request.user)
            addr.is_default = True
            addr.save()
        next_url = request.POST.get("next", request.META.get("HTTP_REFERER", reverse("users:profile")))
        return redirect(next_url)
    return redirect("users:profile")

def _login_next_url(request):
    next_url = request.POST.get("next") or request.GET.get("next") or "/"
    if url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return next_url
    return "/"


def login_view(request):
    next_url = _login_next_url(request)
    if request.method == "POST":
        from django.contrib.auth import authenticate, login
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        errors = {}
        if not email:
            errors["email"] = "Поле должно быть действительным электронным адресом."
        if not password:
            errors["password"] = "Количество символов в поле должно быть не меньше 6."
        if errors:
            return render(request, "users/login.html", {
                "post_data": request.POST,
                "field_errors": errors,
                "next_url": next_url,
            })
        from apps.users.models import User
        candidate = User.objects.filter(email__iexact=email).first()
        if candidate is not None and candidate.check_password(password) and candidate.is_banned_now:
            ban_text = candidate.ban_message()
            messages.error(request, ban_text)
            return render(request, "users/login.html", {
                "post_data": request.POST,
                "field_errors": {"password": ban_text},
                "next_url": next_url,
            })
        user = authenticate(request, username=email, password=password)
        if user is None:
            messages.error(request, "Неверный email или пароль")
            return render(request, "users/login.html", {
                "post_data": request.POST,
                "field_errors": {"password": "Неверный email или пароль"},
                "next_url": next_url,
            })
        from apps.users.verification import is_email_confirmation_enabled
        if is_email_confirmation_enabled() and not user.email_confirmed:
            request.session["verify_email"] = email
            send_verification_email(user, request=request)
            messages.error(request, "Подтвердите email перед входом. Код отправлен на почту.")
            return redirect("users:verify_email")
        login(request, user)
        return redirect(next_url)
    return render(request, "users/login.html", {"next_url": next_url})


def register(request):
    if request.method == "POST":
        from django.contrib.auth import login
        from apps.users.models import User
        from .phone_confirmation import normalize_phone, phone_owner

        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        password2 = request.POST.get("password2", "")
        full_name = request.POST.get("full_name", "").strip()
        phone_raw = request.POST.get("phone", "").strip()
        phone_code = request.POST.get("phone_code", "").strip()
        phone_digits = re.sub(r"[^0-9]", "", phone_raw)
        phone = normalize_phone(phone_raw, phone_code)
        errors = {}
        if not full_name:
            errors["full_name"] = "Количество символов в поле должно быть не меньше 1."
        if not email:
            errors["email"] = "Поле должно быть действительным электронным адресом."
        elif not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            errors["email"] = "Поле должно быть действительным электронным адресом."
        if not phone or len(phone_digits) < 7:
            errors["phone"] = "Введите корректный номер телефона."
        def _password_is_strong(pwd):
            if not pwd or len(pwd) < 8:
                return False
            if not re.search(r'[a-zA-Zа-яА-Я]', pwd):
                return False
            if not re.search(r'[0-9]', pwd):
                return False
            return True

        if not password:
            errors["password"] = "Введите пароль."
        elif not _password_is_strong(password):
            errors["password"] = "Пароль слишком простой: минимум 8 символов, буквы и цифры."
        if not password2:
            errors["password2"] = "Повторите пароль."
        elif password != password2:
            errors["password2"] = "Пароли не совпадают"
        if errors:
            return render(request, "users/register.html", {
                "post_data": request.POST,
                "field_errors": errors,
            })
        if not request.POST.get("agree_terms"):
            messages.error(
                request,
                "Для регистрации необходимо согласиться с условиями оферты и политикой конфиденциальности.",
            )
            return render(request, "users/register.html", {"post_data": request.POST})
        if User.objects.filter(email=email).exists():
            errors["email"] = "Пользователь с таким email уже существует"
            return render(request, "users/register.html", {
                "post_data": request.POST,
                "field_errors": errors,
            })
        if phone_owner(phone):
            errors["phone"] = "Этот номер уже используется другой учётной записью"
            return render(request, "users/register.html", {
                "post_data": request.POST,
                "field_errors": errors,
            })
        user = User.objects.create_user(
            email=email,
            password=password,
            first_name=full_name.split()[0] if full_name else "",
            last_name=" ".join(full_name.split()[1:]) if full_name and len(full_name.split()) > 1 else "",
            phone=phone,
            phone_confirmed=bool(phone),
        )
        request.session["verify_email"] = email
        from apps.users.verification import is_email_confirmation_enabled
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
            return redirect("users:profile")
    return render(request, "users/register.html")


def verify_email(request):
    """Confirm email via OTP code. Works for both logged-in and unauthenticated users."""
    if request.method == "POST":
        code = request.POST.get("code", "").strip()
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
            return redirect("login")
        success, error = verify_otp_code(user, code)
        if success:
            if user.email_confirmed:
                messages.info(request, "Ваш email уже подтверждён.")
            else:
                user.email_confirmed = True
                user.save(update_fields=["email_confirmed"])
                messages.success(request, "Email успешно подтверждён!")
            request.session.pop("verify_email", None)
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            return redirect("users:profile")
        else:
            messages.error(request, error or "Неверный код. Попробуйте снова.")
            return render(request, "users/verify_email.html", {"email": user.email, "message": "Неверный код. Попробуйте снова."})
    email = request.session.get("verify_email", "")
    if request.user.is_authenticated:
        email = request.user.email
    return render(request, "users/verify_email.html", {"email": email, "message": "Введите 6-значный код из письма."})


@require_POST
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
    else:
        last_sent = _latest_verification_email(user.email)
        if last_sent is not None:
            elapsed = (timezone.now() - last_sent.sent_at).total_seconds()
            if elapsed < RESEND_COOLDOWN_SECONDS:
                wait = int(RESEND_COOLDOWN_SECONDS - elapsed)
                messages.warning(request, f"Письмо уже отправлено. Повторно можно запросить через {wait} сек.")
                return _resend_response(request, sent=False)
        sent_ok = send_verification_email(user, request=request)
        if sent_ok:
            messages.success(request, f"Письмо отправлено на {user.email}. Проверьте папку «Спам».")
        else:
            messages.error(request, "Не удалось отправить письмо. Попробуйте позже или напишите в поддержку.")
    return _resend_response(request, sent=sent_ok)


def _resend_response(request, sent):
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        from django.http import JsonResponse
        return JsonResponse({"sent": sent})
    if request.headers.get("HX-Request"):
        return render(request, "users/partials/resend_verification_status.html", {"sent": sent})
    return redirect("users:verify_email")


def _latest_verification_email(email):
    marker = "код"
    candidates = EmailLog.objects.filter(recipient=email, success=True).order_by("-sent_at")[:50]
    for log in candidates:
        if marker in log.subject.lower():
            return log
    return None

@login_required
def add_to_wishlist(request, product_id):
    from apps.catalog.models import Product
    product = get_object_or_404(Product, id=product_id)
    Wishlist.objects.get_or_create(user=request.user, product=product)
    return redirect(request.META.get("HTTP_REFERER", "users:wishlist"))

@login_required
def remove_from_wishlist(request, product_id):
    Wishlist.objects.filter(user=request.user, product_id=product_id).delete()
    if request.headers.get("HX-Request"):
        items = Wishlist.objects.filter(user=request.user).select_related("product").order_by("-added_at")[:4]
        total = Wishlist.objects.filter(user=request.user).count()
        response = render(request, "users/partials/mini_wishlist.html", {"wishlist_items": items, "total": total})
        response["HX-Trigger"] = json.dumps({"wishlistUpdated": {"count": total}})
        return response
    return redirect(request.META.get("HTTP_REFERER", "users:wishlist"))

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

@require_http_methods(["GET", "POST"])
def custom_logout(request):
    wish_ids = []
    cart_items = []
    if request.user.is_authenticated:
        from apps.orders.models import Wishlist, Cart, CartItem
        wish_ids = list(Wishlist.objects.filter(user=request.user).values_list("product_id", flat=True))
        try:
            cart = request.user.cart
            cart_items = list(cart.items.values_list("variant_id", "qty"))
        except Cart.DoesNotExist:
            pass
    logout(request)
    if cart_items:
        from apps.orders.models import Cart as CartModel, CartItem as CartItemModel
        from apps.catalog.models import ProductVariant
        if not request.session.session_key:
            request.session.create()
        new_cart = CartModel.objects.create(session_key=request.session.session_key)
        for vid, qty in cart_items:
            if ProductVariant.objects.filter(id=vid).exists():
                CartItemModel.objects.create(cart=new_cart, variant_id=vid, qty=qty)
    if wish_ids:
        import json
        from django.http import HttpResponse
        ids_json = json.dumps(wish_ids)
        html = ('<!DOCTYPE html><html><head><meta charset="utf-8"></head><body>'
                '<script>localStorage.setItem("wishlist", JSON.stringify(' + ids_json + '));'
                'window.location.href="/";</script></body></html>')
        return HttpResponse(html)
    return redirect("/")

@require_POST
def wishlist_toggle(request):
    from django.http import JsonResponse
    from apps.catalog.models import Product
    if not request.user.is_authenticated:
        return JsonResponse({"error": "login_required", "redirect": "/login/"}, status=401)
    product_id = request.POST.get("product_id")
    add = request.POST.get("add", "true").lower() in ("true", "1", "yes")
    if not product_id:
        return JsonResponse({"error": "product_id required"}, status=400)
    product = get_object_or_404(Product, id=product_id)
    if add:
        Wishlist.objects.get_or_create(user=request.user, product=product)
    else:
        Wishlist.objects.filter(user=request.user, product=product).delete()
    count = Wishlist.objects.filter(user=request.user).count()
    return JsonResponse({"ok": True, "product_id": product_id, "in_wishlist": add, "total_count": count})


@require_POST
def sync_local_storage(request):
    import json
    from django.http import JsonResponse
    from apps.catalog.models import Product
    if not request.user.is_authenticated:
        return JsonResponse({"error": "login_required"}, status=401)
    try:
        payload = json.loads(request.body or b"{}")
    except (ValueError, TypeError):
        return JsonResponse({"error": "invalid_json"}, status=400)
    from apps.orders.models import ProductNote
    wishlist_ids = [int(x) for x in payload.get("wishlist", []) if str(x).isdigit()]
    added = 0
    if wishlist_ids:
        existing = set(Product.objects.filter(id__in=wishlist_ids, is_active=True).values_list("id", flat=True))
        for pid in existing:
            _, created = Wishlist.objects.get_or_create(user=request.user, product_id=pid)
            if created:
                added += 1
    notes_data = payload.get("notes", {})
    notes_synced = 0
    if isinstance(notes_data, dict):
        for pid_str, text in notes_data.items():
            if str(pid_str).isdigit() and text and str(text).strip():
                ProductNote.objects.update_or_create(user=request.user, product_id=int(pid_str), defaults={"text": str(text).strip()})
                notes_synced += 1
    from apps.orders.models import Cart, CartItem
    from apps.catalog.models import ProductVariant
    cart_items_data = payload.get("cart_items", [])
    cart_items_synced = 0
    if isinstance(cart_items_data, list) and cart_items_data:
        user_cart, _ = Cart.objects.get_or_create(user=request.user)
        for item in cart_items_data:
            try:
                vid = int(item.get("variant_id", 0))
                qty = max(1, int(item.get("qty", 1)))
                variant = ProductVariant.objects.filter(id=vid).first()
                if variant:
                    ci, created = CartItem.objects.get_or_create(cart=user_cart, variant=variant, defaults={"qty": qty})
                    if not created:
                        ci.qty += qty
                        ci.save(update_fields=["qty"])
                    cart_items_synced += 1
            except (ValueError, TypeError):
                continue
    return JsonResponse({
        "ok": True,
        "wishlist_added": added,
        "wishlist_count": Wishlist.objects.filter(user=request.user).count(),
        "notes_synced": notes_synced,
        "cart_items_synced": cart_items_synced,
    })


@login_required
@login_required
def discount_view(request):
    from django.db.models import Sum
    from apps.orders.models import Order
    user = request.user
    qs = Order.objects.filter(user=user).exclude(status=Order.STATUS_CANCELLED)
    total_spent = qs.aggregate(t=Sum("total_amount"))["t"] or 0
    orders_count = qs.count()
    # Фиксированная скидка назначается вручную в админке (User.wholesale_discount).
    # Применяется ко всем заказам пользователя автоматически.
    current_discount = user.wholesale_discount or 0
    return render(request, "users/discount.html", {
        "section": "discount",
        "current_discount": current_discount,
        "total_spent": total_spent,
        "orders_count": orders_count,
    })


@login_required
def balance_view(request):
    from apps.users.models import BonusTransaction, PaymentTransaction
    from django.conf import settings
    from django.utils import timezone
    from django.db import transaction
    user = request.user
    if hasattr(settings, "YOOKASSA_SHOP_ID") and settings.YOOKASSA_SHOP_ID:
        pending_txs = PaymentTransaction.objects.filter(user=user, status="pending")
        for tx in pending_txs:
            try:
                from yookassa import Configuration, Payment as YooPayment
                Configuration.account_id = settings.YOOKASSA_SHOP_ID
                Configuration.secret_key = settings.YOOKASSA_SECRET_KEY
                payment_data = YooPayment.find_one(tx.payment_id)
                if payment_data.status == "succeeded":
                    with transaction.atomic():
                        tx = PaymentTransaction.objects.select_for_update().get(id=tx.id)
                        if tx.status != "completed":
                            from decimal import Decimal
                            user.balance += tx.amount
                            user.save(update_fields=["balance"])
                            tx.status = "completed"
                            tx.completed_at = timezone.now()
                            tx.save(update_fields=["status", "completed_at"])
                            from django.contrib import messages
                            messages.success(request, f"Баланс пополнен на {tx.amount} ₽")
            except Exception:
                pass
    user.expire_old_bonus()
    available_points = user.get_available_bonus_points()
    transactions = BonusTransaction.objects.filter(user=user).select_related("order")[:20]
    return render(request, "users/balance.html", {
        "section": "balance",
        "transactions": transactions,
        "available_points": available_points,
    })


@login_required
def promo_view(request):
    return render(request, "users/promo.html", {"section": "promo"})


@login_required
def navigation_view(request):
    return render(request, "users/navigation.html", {"section": "navigation"})


@login_required
def statistics_view(request):
    from django.db.models import Sum, Count
    from decimal import Decimal
    from apps.orders.models import Order
    user = request.user
    qs = Order.objects.filter(user=user)
    active_qs = qs.exclude(status=Order.STATUS_CANCELLED)
    stats = {
        "orders_total": qs.count(),
        "orders_active": qs.exclude(status__in=[Order.STATUS_DELIVERED, Order.STATUS_COMPLETED, Order.STATUS_CANCELLED]).count(),
        "orders_completed": qs.filter(status__in=[Order.STATUS_DELIVERED, Order.STATUS_COMPLETED]).count(),
        "orders_cancelled": qs.filter(status=Order.STATUS_CANCELLED).count(),
        "total_spent": active_qs.aggregate(t=Sum("total_amount"))["t"] or Decimal("0"),
        "wishlist_count": user.wishlist_set.count() if hasattr(user, "wishlist_set") else 0,
        "addresses_count": user.addresses.count(),
        "bonus_points": user.bonus_points,
        "balance": user.balance,
        "discount_pct": user.wholesale_discount or 0,
        "is_wholesale": user.is_wholesale,
    }
    return render(request, "users/statistics.html", {"section": "statistics", "stats": stats})


@login_required
def notifications_view(request):
    from apps.users.models import UserNotification
    notifs = list(
        UserNotification.objects.filter(user=request.user)
        .select_related("actor")
        .order_by("-created_at")[:100]
    )
    UserNotification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return render(request, "users/notifications.html", {"section": "notifications", "notifications": notifs})


def mini_notifications(request):
    from apps.users.models import UserNotification
    if not request.user.is_authenticated:
        return render(request, "users/partials/mini_notifications.html", {"notifications": [], "total": 0})
    qs = UserNotification.objects.filter(user=request.user).select_related("actor").order_by("-created_at")
    notifs = list(qs[:5])
    total = qs.count()
    UserNotification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return render(request, "users/partials/mini_notifications.html", {"notifications": notifs, "total": total})


@never_cache
def service_worker(request):
    """Старый адрес воркера. Снимает прошлую регистрацию, чтобы не спорил с /sw.js."""
    body = (
        "self.addEventListener('install', function () { self.skipWaiting(); });\n"
        "self.addEventListener('activate', function (event) {\n"
        "  event.waitUntil(self.registration.unregister());\n"
        "});\n"
    )
    response = HttpResponse(body, content_type="application/javascript")
    response["Service-Worker-Allowed"] = "/"
    response["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response


@never_cache
def pwa_worker(request):
    from django.conf import settings
    from pathlib import Path

    script = Path(settings.BASE_DIR) / "static" / "sw.js"
    response = HttpResponse(script.read_bytes(), content_type="application/javascript")
    response["Service-Worker-Allowed"] = "/"
    response["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response


@login_required
def push_config(request):
    from django.conf import settings

    return JsonResponse({"public_key": getattr(settings, "WEBPUSH_VAPID_PUBLIC_KEY", "")})


@login_required
@require_POST
def push_subscribe(request):
    from apps.users.models import PushSubscription

    try:
        payload = json.loads(request.body or "{}")
        endpoint = payload["endpoint"]
        keys = payload["keys"]
        p256dh = keys["p256dh"]
        auth_key = keys["auth"]
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return JsonResponse({"ok": False, "error": "invalid_subscription"}, status=400)

    subscription, _ = PushSubscription.objects.update_or_create(
        endpoint=endpoint,
        defaults={
            "user": request.user,
            "p256dh": p256dh,
            "auth": auth_key,
            "user_agent": request.headers.get("User-Agent", "")[:500],
            "is_active": True,
        },
    )
    return JsonResponse({"ok": True, "subscription_id": subscription.pk})


@login_required
@require_POST
def push_unsubscribe(request):
    from apps.users.models import PushSubscription

    try:
        endpoint = json.loads(request.body or "{}").get("endpoint", "")
    except json.JSONDecodeError:
        endpoint = ""
    if endpoint:
        PushSubscription.objects.filter(user=request.user, endpoint=endpoint).update(is_active=False)
    return JsonResponse({"ok": True})


@login_required
def community_profile_view(request):
    from apps.pages.models import CommunityPost, CommunityPostLike
    user_posts = CommunityPost.objects.filter(user=request.user).order_by("-created_at")[:20]
    all_count = CommunityPost.objects.filter(user=request.user).count()
    like_count = CommunityPostLike.objects.filter(post__user=request.user).exclude(user=request.user).count()
    community_stats = {"post_count": all_count, "review_count": request.user.reviews.count(), "like_count": like_count}
    return render(request, "users/community_profile.html", {
        "section": "community",
        "user_posts": user_posts,
        "community_stats": community_stats,
    })


@login_required
def subscriptions_view(request):
    return redirect("users:profile")


@login_required
def blacklist_view(request):
    blocked = request.user.blocked_users.all() if hasattr(request.user, "blocked_users") else []
    return render(request, "users/blacklist.html", {"section": "blacklist", "blocked_users": blocked})


@login_required
def topup_balance(request):
    if request.method == "POST":
        amount_raw = request.POST.get("amount", "0").replace(",", ".").strip()
        try:
            from decimal import Decimal, InvalidOperation
            amount = Decimal(amount_raw)
        except (InvalidOperation, ValueError):
            messages.error(request, "Введите корректную сумму")
            return redirect("users:balance")
        if amount < 100:
            messages.error(request, "Минимальная сумма пополнения — 100 ₽")
            return redirect("users:balance")
        if amount > 100000:
            messages.error(request, "Максимальная сумма пополнения — 100 000 ₽")
            return redirect("users:balance")

        try:
            from yookassa import Configuration, Payment
            from django.conf import settings
            import uuid

            if not hasattr(settings, "YOOKASSA_SHOP_ID") or not settings.YOOKASSA_SHOP_ID:
                messages.error(request, "ЮKassa не настроена. Обратитесь к администратору.")
                return redirect("users:balance")

            Configuration.account_id = settings.YOOKASSA_SHOP_ID
            Configuration.secret_key = settings.YOOKASSA_SECRET_KEY

            payment = Payment.create({
                "amount": {
                    "value": str(amount),
                    "currency": "RUB"
                },
                "confirmation": {
                    "type": "redirect",
                    "return_url": request.build_absolute_uri("/account/balance/")
                },
                "capture": True,
                "description": f"Пополнение баланса: {request.user.email}",
                "metadata": {
                    "user_id": request.user.id
                }
            }, str(uuid.uuid4()))

            from apps.users.models import PaymentTransaction
            PaymentTransaction.objects.create(
                user=request.user,
                payment_id=payment.id,
                amount=amount,
                status="pending",
                provider="yookassa"
            )
            return redirect(payment.confirmation.confirmation_url)
        except Exception as e:
            messages.error(request, f"Ошибка платежной системы: {str(e)}")
            return redirect("users:balance")
    return redirect("users:balance")

@login_required
@require_POST
def unblock_user(request, pk):
    from django.http import HttpResponse
    if hasattr(request.user, "blocked_users"):
        blocked = request.user.blocked_users.filter(pk=pk)
        if blocked.exists():
            request.user.blocked_users.remove(blocked.first())
            messages.success(request, "Пользователь разблокирован")
    if request.headers.get("HX-Request"):
        return HttpResponse("")
    return redirect(request.META.get("HTTP_REFERER", "users:blacklist"))


@login_required
@require_POST
def dismiss_notice(request, key):
    from django.http import HttpResponse
    dismissed = request.session.get("dismissed_notices", [])
    if key not in dismissed:
        dismissed.append(key)
        request.session["dismissed_notices"] = dismissed
    if request.headers.get("HX-Request"):
        return HttpResponse("")
    return redirect(request.META.get("HTTP_REFERER", "users:profile"))


@login_required
def wishlist_count(request):
    from django.http import JsonResponse
    from apps.orders.models import Wishlist
    count = Wishlist.objects.filter(user=request.user).count()
    return JsonResponse({"count": count})


@login_required
@require_POST
def save_note(request, product_id):
    from django.http import JsonResponse
    from apps.orders.models import ProductNote
    from apps.catalog.models import Product
    product = get_object_or_404(Product, id=product_id)
    text = request.POST.get("text", "").strip()
    if text:
        note, created = ProductNote.objects.update_or_create(user=request.user, product=product, defaults={"text": text})
        return JsonResponse({"ok": True, "created": created, "text": note.text})
    else:
        ProductNote.objects.filter(user=request.user, product=product).delete()
        return JsonResponse({"ok": True, "deleted": True})


@login_required
@require_POST
def delete_note(request, product_id):
    from django.http import JsonResponse
    from apps.orders.models import ProductNote
    from apps.catalog.models import Product
    product = get_object_or_404(Product, id=product_id)
    ProductNote.objects.filter(user=request.user, product=product).delete()
    return JsonResponse({"ok": True, "deleted": True})


    from django.shortcuts import get_object_or_404
    from apps.users.models import User as ProfileUser
    profile_user = get_object_or_404(ProfileUser, public_username=username)


# --- Account-unlock-via-email (django-axes lockout self-service) ---
# See config/settings/base.py AXES_LOCKOUT_URL -> this view. django-axes locks out by
# ip_address (default AXES_LOCKOUT_PARAMETERS), so on success we reset by both the
# submitted email/username and the current request IP to cover the common case
# (same device/network retrying) without over-broadening the reset.

def unlock_account(request):
    """Self-service unlock: user enters their account email, we email a 6-digit code
    (reusing the OTP-style flow in apps/users/verification.py), and on correct entry we
    clear the axes lockout for that email (and the current IP) so they can log in again.

    Does not reveal whether the email exists (avoids user enumeration): always shows the
    same "code sent if the account exists" message and always redirects to the code-entry
    step, whether or not a matching user was found.
    """
    from apps.users.models import User as AppUser
    from axes.utils import reset as axes_reset

    step = request.session.get("unlock_step", "request")
    email = request.session.get("unlock_email", "")
    if not email:
        # axes redirects here with ?username=<value> on lockout (AXES_LOCKOUT_URL) -
        # prefill so the user doesn't have to retype the email they just tried.
        email = request.GET.get("username", "").strip()

    if request.method == "POST":
        action = request.POST.get("action", "request_code")

        if action == "request_code":
            email = request.POST.get("email", "").strip().lower()
            if not email:
                messages.error(request, "Введите email")
                return render(request, "users/unlock_account.html", {"step": "request"})
            request.session["unlock_email"] = email
            request.session["unlock_step"] = "code"
            try:
                user = AppUser.objects.get(email__iexact=email)
                send_unlock_email(user, request=request)
            except AppUser.DoesNotExist:
                pass  # same response either way — no user enumeration
            messages.success(
                request,
                "Если такой аккаунт существует, на почту отправлен код разблокировки.",
            )
            return redirect("unlock_account")

        elif action == "verify_code":
            code = request.POST.get("code", "").strip()
            if not email:
                messages.error(request, "Сессия истекла, начните заново.")
                request.session.pop("unlock_step", None)
                return redirect("unlock_account")
            success, error = verify_unlock_code(email, code)
            if success:
                try:
                    user = AppUser.objects.get(email__iexact=email)
                    axes_reset(username=user.email)
                except AppUser.DoesNotExist:
                    axes_reset(username=email)
                client_ip = request.META.get("REMOTE_ADDR")
                if client_ip:
                    axes_reset(ip=client_ip)
                request.session.pop("unlock_email", None)
                request.session.pop("unlock_step", None)
                messages.success(request, "Аккаунт разблокирован. Теперь вы можете войти.")
                return redirect("login")
            else:
                messages.error(request, error or "Неверный код. Попробуйте снова.")
                return render(request, "users/unlock_account.html", {"step": "code", "email": email})

    return render(request, "users/unlock_account.html", {"step": step, "email": email})


@require_POST
def resend_unlock_code(request):
    from apps.users.models import User as AppUser

    email = request.session.get("unlock_email", "")
    if not email:
        messages.error(request, "Сессия истекла, начните заново.")
        return redirect("unlock_account")

    last_sent = _latest_verification_email(email)
    if last_sent is not None:
        elapsed = (timezone.now() - last_sent.sent_at).total_seconds()
        if elapsed < UNLOCK_RESEND_COOLDOWN_SECONDS:
            wait = int(UNLOCK_RESEND_COOLDOWN_SECONDS - elapsed)
            messages.warning(request, f"Код уже отправлен. Повторно можно запросить через {wait} сек.")
            return redirect("unlock_account")

    try:
        user = AppUser.objects.get(email__iexact=email)
        send_unlock_email(user, request=request)
    except AppUser.DoesNotExist:
        pass
    messages.success(request, "Если такой аккаунт существует, код отправлен повторно.")
    return redirect("unlock_account")
