from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.urls import reverse
from .cart_service import CartService
from .checkout_service import CheckoutService
from django.http import HttpResponse
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import Cart, Order
from apps.catalog.models import SiteSettings
from apps.users.models import Address, User


def _phone_digits(value):
    return "".join(ch for ch in (value or "") if ch.isdigit())


def _registered_checkout_users(email, phone):
    """Return matching account(s) without trusting formatting of stored phones."""
    matches = {}
    if email:
        for user in User.objects.filter(email__iexact=email):
            matches[user.pk] = user

    phone_digits = _phone_digits(phone)
    if phone_digits:
        for user in User.objects.exclude(phone="").only(
            "pk", "email", "phone", "password", "is_active"
        ):
            if _phone_digits(user.phone) == phone_digits:
                matches[user.pk] = user
    return list(matches.values())


def _validate_checkout_password(password, password_repeat):
    if password != password_repeat:
        raise ValueError("Пароли не совпадают")
    if len(password) < 8:
        raise ValueError("Пароль должен содержать минимум 8 символов")
    if not any(ch.isalpha() for ch in password) or not any(ch.isdigit() for ch in password):
        raise ValueError("Пароль должен содержать буквы и цифры")
    if password.lower() in {
        "password",
        "password1",
        "12345678",
        "qwertyui",
        "qwerty123",
        "11111111",
    }:
        raise ValueError("Сделайте пароль сложнее")


@require_POST
def checkout_account_status(request):
    """Tell checkout whether entered contacts belong to an existing account.

    The final decision is always repeated in ``basket_view``.  This endpoint is
    only an early UI hint, so a stale or interrupted request cannot bypass the
    server-side protection against guest orders for registered contacts.
    """
    if request.user.is_authenticated:
        return JsonResponse({"exists": False, "conflict": False})

    email = (request.POST.get("email") or "").strip()
    phone = (request.POST.get("phone") or "").strip()
    matches = _registered_checkout_users(email, phone)
    return JsonResponse({
        "exists": bool(matches),
        "conflict": len(matches) > 1,
    })

def basket_view(request):
    site_settings = SiteSettings.load()
    from apps.orders.recurring import recurring_payments_enabled

    recurring_enabled = recurring_payments_enabled()
    enabled_delivery_types = site_settings.enabled_delivery_types()
    default_delivery_type = site_settings.default_delivery_type()
    cart_service = CartService(request)
    if request.GET.get("remove_promo"):
        cart_service.remove_promo()
        messages.success(request, "Промо-код удалён")
    cart = cart_service.get_cart()

    # Handle bulk delete selected items
    if request.method == "POST" and request.POST.get("action") == "delete_selected":
        selected_ids = request.POST.getlist("selected_items")
        for variant_id in selected_ids:
            cart_service.remove(variant_id)
        messages.success(request, "Выбранные товары удалены из корзины")
        return redirect("orders:basket")

    # Handle order placement (checkout)
    if request.method == "POST" and request.POST.get("action") == "checkout":
        if not cart or cart.total_items == 0:
            return redirect("orders:basket")
        checkout = CheckoutService(request)
        try:
            # Extract and split names, handling both mobile and desktop form fields
            full_name = (request.POST.get("full_name") or request.POST.get("full_name_m") or "").strip()
            first_name = request.POST.get("first_name", "")
            last_name = request.POST.get("last_name", "")
            if full_name and not first_name:
                parts = full_name.split(None, 1)
                first_name = parts[0]
                if len(parts) > 1:
                    last_name = parts[1]

            phone = (request.POST.get("phone", "") or request.POST.get("phone_m", "")).strip()
            phone_code = request.POST.get("phone_code", "+7")
            raw_phone_digits = "".join(ch for ch in phone if ch.isdigit())
            if len(raw_phone_digits) < 7:
                raise ValueError("Укажите корректный телефон")
            code_digits = "".join(ch for ch in phone_code if ch.isdigit())
            if raw_phone_digits.startswith(code_digits):
                phone = f"{phone_code}{raw_phone_digits[len(code_digits):]}"
            else:
                phone = f"{phone_code}{raw_phone_digits}"
            email = (request.POST.get("email", "") or request.POST.get("email_m", "")).strip()
            city = (request.POST.get("city", "") or request.POST.get("city_m", "")).strip()
            street = (request.POST.get("street", "") or request.POST.get("street_m", "")).strip()
            apartment = (request.POST.get("apartment", "") or request.POST.get("apt_m", "")).strip()
            house = (request.POST.get("house", "") or request.POST.get("house_m", "")).strip()
            postal_code = (request.POST.get("postal_code", "") or request.POST.get("postal_code_m", "")).strip()
            is_address_main = request.POST.get("is_address_main") == "on"
            selected_address_id = request.POST.get("selected_address_id", "")
            if not request.user.is_authenticated:
                selected_address_id = ""
            if (
                request.user.is_authenticated
                and selected_address_id
                and selected_address_id != "null"
                and selected_address_id.isdigit()
            ):
                try:
                    addr = Address.objects.get(id=selected_address_id, user=request.user)
                    if not city:
                        city = addr.city
                    if not street:
                        street = addr.street
                    if not apartment:
                        apartment = addr.apartment
                    if not house and hasattr(addr, "house"):
                        house = addr.house or ""
                    if not postal_code and hasattr(addr, "postal_code"):
                        postal_code = addr.postal_code or ""
                except Address.DoesNotExist:
                    pass
            delivery_type = request.POST.get("delivery_type", default_delivery_type)
            payment_method = request.POST.get("payment_method", "card")
            repeat_requested = request.POST.get("repeat_order") == "on"
            try:
                repeat_weeks = int(request.POST.get("repeat_weeks", "1"))
            except (TypeError, ValueError):
                repeat_weeks = 1
            repeat_weeks = max(1, min(repeat_weeks, 12))

            if not request.POST.get("agree_terms"):
                raise ValueError("Подтвердите согласие с условиями обработки данных, пользовательского соглашения и оферты")
            if not first_name.strip():
                raise ValueError("Укажите имя и фамилию")
            try:
                validate_email(email)
            except ValidationError:
                raise ValueError("Укажите корректную электронную почту")
            if delivery_type not in enabled_delivery_types:
                raise ValueError("Выбранный способ доставки сейчас недоступен")
            if payment_method not in dict(Order.PAYMENT_CHOICES):
                raise ValueError("Выберите способ оплаты")
            if repeat_requested and payment_method != Order.PAYMENT_CARD:
                raise ValueError("Автоповтор доступен только при оплате картой на сайте")
            if repeat_requested and not recurring_enabled:
                raise ValueError("Автоповтор заказов временно отключён администратором")

            if request.user.is_authenticated:
                if User.objects.filter(email__iexact=email).exclude(pk=request.user.pk).exists():
                    raise ValueError("Эта электронная почта уже используется другой учётной записью")
                phone_matches = [
                    user for user in _registered_checkout_users("", phone)
                    if user.pk != request.user.pk
                ]
                if phone_matches:
                    raise ValueError("Этот номер телефона уже используется другой учётной записью")

            cdek_types = (Order.DELIVERY_CDEK_PVZ, Order.DELIVERY_CDEK_DOOR)
            if delivery_type not in (Order.DELIVERY_PICKUP, *cdek_types) and not selected_address_id:
                if not city:
                    raise ValueError("Укажите город")
                if not street:
                    raise ValueError("Укажите улицу")
                if not house:
                    raise ValueError("Укажите номер дома")
                if not postal_code:
                    raise ValueError("Укажите индекс")
            if delivery_type == Order.DELIVERY_CDEK_PVZ and not request.POST.get("cdek_pvz_code"):
                raise ValueError("Выберите пункт выдачи СДЭК")
            cdek_city_code = (request.POST.get("cdek_city_code") or "").strip()
            cdek_city_name = (request.POST.get("cdek_city_name") or "").strip()
            if delivery_type in cdek_types:
                if not cdek_city_code or not cdek_city_name:
                    raise ValueError("Выберите город из списка СДЭК")
                city = cdek_city_name
                street = (request.POST.get("cdek_street") or street).strip()
                house = (request.POST.get("cdek_house") or house).strip()
                apartment = (request.POST.get("cdek_apartment") or apartment).strip()
                postal_code = (request.POST.get("cdek_postal_code") or postal_code).strip()
            if delivery_type == Order.DELIVERY_CDEK_DOOR:
                if not street:
                    raise ValueError("Укажите улицу для доставки СДЭК")
                if not house:
                    raise ValueError("Укажите номер дома для доставки СДЭК")
                if not postal_code:
                    raise ValueError("Укажите индекс для доставки СДЭК")

            order_user = request.user if request.user.is_authenticated else None
            login_after_order = None
            if not request.user.is_authenticated:
                registered_users = _registered_checkout_users(email, phone)
                register_account = request.POST.get("register_account") == "on"
                reg_pwd = request.POST.get("reg_password", "")
                reg_pwd2 = request.POST.get("reg_password2", "")

                if registered_users:
                    if len(registered_users) > 1:
                        raise ValueError(
                            "Почта и телефон принадлежат разным аккаунтам. "
                            "Войдите в аккаунт и повторите оформление заказа"
                        )
                    if not register_account:
                        raise ValueError(
                            "Аккаунт с этой почтой или телефоном уже существует. "
                            "Отметьте «Войти в существующий аккаунт» и введите пароль"
                        )
                    if not reg_pwd:
                        raise ValueError("Введите пароль от существующего аккаунта")
                    if not registered_users[0].check_password(reg_pwd):
                        raise ValueError("Неверный пароль от существующего аккаунта")
                    order_user = registered_users[0]
                    login_after_order = registered_users[0]
                elif register_account:
                    _validate_checkout_password(reg_pwd, reg_pwd2)
                    try:
                        new_user = User.objects.create_user(
                            email=email,
                            password=reg_pwd,
                            first_name=first_name,
                            last_name=last_name,
                            phone=phone,
                        )
                    except IntegrityError as exc:
                        raise ValueError(
                            "Аккаунт с этой почтой или телефоном уже существует. "
                            "Обновите страницу и войдите в него"
                        ) from exc
                    order_user = new_user
                    login_after_order = new_user

            if repeat_requested and order_user is None:
                raise ValueError(
                    "Для автоповтора войдите в аккаунт или зарегистрируйтесь при оформлении"
                )

            cdek_delivery_cost = request.POST.get("cdek_delivery_cost", "0")
            if delivery_type in cdek_types:
                from apps.delivery.cdek import CDEKClient

                total_weight = 0
                for item in cart.items.select_related("variant"):
                    item_weight = item.variant.weight if item.variant and item.variant.weight else 300
                    total_weight += int(item_weight) * item.qty
                cdek_result = CDEKClient().calc_delivery_cost(
                    to_city_code=int(cdek_city_code),
                    weight_grams=max(total_weight, 100),
                    delivery_type=delivery_type,
                    to_address=f"{street}, д. {house}" if street and house else street,
                    to_postal_code=postal_code or None,
                )
                if "error" in cdek_result:
                    raise ValueError(
                        "СДЭК не смог проверить адрес и стоимость доставки. "
                        "Проверьте адрес и попробуйте ещё раз"
                    )
                cdek_delivery_cost = cdek_result["cost"]

            other_recipient = request.POST.get("other_recipient") == "on"
            recipient_name = request.POST.get("recipient_name", "").strip()
            recipient_phone = request.POST.get("recipient_phone", "").strip()
            if other_recipient:
                if not recipient_name:
                    raise ValueError("Укажите имя другого получателя")
                recipient_digits = "".join(ch for ch in recipient_phone if ch.isdigit())
                if len(recipient_digits) < 7:
                    raise ValueError("Укажите корректный телефон другого получателя")
                recipient_code = request.POST.get("recipient_phone_code", "+7").strip() or "+7"
                recipient_code_digits = "".join(ch for ch in recipient_code if ch.isdigit())
                if recipient_digits.startswith(recipient_code_digits):
                    recipient_phone = f"{recipient_code}{recipient_digits[len(recipient_code_digits):]}"
                else:
                    recipient_phone = f"{recipient_code}{recipient_digits}"
            else:
                recipient_name = ""
                recipient_phone = ""

            data = {
                "delivery_type": delivery_type,
                "payment_method": payment_method,
                "first_name": first_name.strip(),
                "last_name": last_name.strip(),
                "phone": phone,
                "email": email,
                "city": city,
                "street": street,
                "house": house,
                "postal_code": postal_code,
                "apartment": apartment,
                "comment": request.POST.get("comment", ""),
                "cdek_pvz_code": request.POST.get("cdek_pvz_code", ""),
                "cdek_pvz_address": request.POST.get("cdek_pvz_address", ""),
                "cdek_city_code": cdek_city_code,
                "cdek_delivery_cost": cdek_delivery_cost,
                "phone_code": request.POST.get("phone_code", "+7"),
                "is_organization": request.POST.get("is_organization", ""),
                "org_name": request.POST.get("org_name", ""),
                "org_inn": request.POST.get("org_inn", ""),
                "recipient_name": recipient_name,
                "recipient_phone": recipient_phone,
            }
            order = checkout.place_order(data, order_user=order_user)

            recurring_plan = None
            if repeat_requested:
                from apps.orders.models import RecurringOrder

                recurring_plan = RecurringOrder.objects.create(
                    source_order=order,
                    user=order_user,
                    interval_weeks=repeat_weeks,
                )

            if login_after_order is not None:
                auth_login(
                    request,
                    login_after_order,
                    backend="django.contrib.auth.backends.ModelBackend",
                )

            messages.success(request, f"Заказ #{order.pk} успешно оформлен!")

            try:
                from apps.orders.tasks import send_order_confirmation
                send_order_confirmation.delay(order.id)
            except Exception as exc:
                import logging as _email_log
                _email_log.getLogger(__name__).error(f"Order confirmation email queue error for order {order.id}: {exc}")

            try:
                from apps.orders.tasks import send_admin_order_notification
                send_admin_order_notification.delay(order.id)
            except Exception as exc:
                import logging as _email_log
                _email_log.getLogger(__name__).error(f"Admin order notification queue error for order {order.id}: {exc}")

            if request.user.is_authenticated:
                org_name_val = data.get("org_name", "").strip()
                org_inn_val = data.get("org_inn", "").strip()
                is_org = data.get("is_organization") == "on" or data.get("is_organization") is True
                if is_org and (org_name_val or org_inn_val):
                    from apps.users.models import User as ProfileUser
                    user_profile = ProfileUser.objects.get(pk=request.user.pk)
                    changed = False
                    if org_name_val:
                        user_profile.company_name = org_name_val
                        changed = True
                    if org_inn_val:
                        user_profile.company_inn = org_inn_val
                        changed = True
                    if changed:
                        user_profile.save(update_fields=["company_name", "company_inn"])
                if city and street and not selected_address_id:
                    if is_address_main:
                        Address.objects.filter(user=request.user, is_default=True).update(is_default=False)
                    addr_obj, _ = Address.objects.update_or_create(
                        user=request.user,
                        city=city,
                        street=street,
                        defaults={
                            "house": house,
                            "apartment": apartment,
                            "postal_code": postal_code,
                            "is_default": is_address_main,
                        }
                    )

            # For COD (cash on delivery) + CDEK: create waybill immediately
            if order.payment_method == "cod" and order.delivery_type in ["cdek_pvz", "cdek_door"]:
                from apps.orders.tasks import create_cdek_waybill
                try:
                    create_cdek_waybill.delay(order.id)
                except Exception as exc:
                    import logging as _cdek_log
                    _cdek_log.getLogger(__name__).error(f"CDEK waybill queue error for order {order.id}: {exc}")

            if order.payment_method in ["card", "sbp"]:
                from django.conf import settings
                shop_id = getattr(settings, "YOOKASSA_SHOP_ID", "")
                secret_key = getattr(settings, "YOOKASSA_SECRET_KEY", "")
                if shop_id and secret_key:
                    import yookassa
                    yookassa.Configuration.account_id = shop_id
                    yookassa.Configuration.secret_key = secret_key
                    import uuid
                    from apps.payments.models import Payment
                    idempotency_key = str(uuid.uuid4())

                    payment_payload = {
                        "amount": {
                            "value": str(order.total_amount),
                            "currency": "RUB",
                        },
                        "confirmation": {
                            "type": "redirect",
                            "return_url": request.build_absolute_uri(
                                reverse("orders:order_success", args=[order.id])
                            ),
                        },
                        "capture": True,
                        "description": f"Заказ #{order.id} — Aspect Coffee",
                        "metadata": {"order_id": str(order.id)},
                    }
                    if recurring_plan is not None:
                        payment_payload["save_payment_method"] = True
                        payment_payload["merchant_customer_id"] = str(order_user.pk)

                    payment_data = yookassa.Payment.create(payment_payload, idempotency_key)

                    payment, _ = Payment.objects.get_or_create(
                        order=order,
                        defaults={
                            "yookassa_id": payment_data.id,
                            "amount": order.total_amount,
                            "status": Payment.STATUS_PENDING,
                            "confirmation_url": payment_data.confirmation.confirmation_url,
                        },
                    )
                    if payment.yookassa_id != payment_data.id:
                        payment.yookassa_id = payment_data.id
                        payment.confirmation_url = payment_data.confirmation.confirmation_url
                        payment.save(update_fields=["yookassa_id", "confirmation_url"])
                    if order.payment_id != payment_data.id:
                        order.payment_id = payment_data.id
                        order.save(update_fields=["payment_id"])

                    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                        from django.http import JsonResponse
                        return JsonResponse({"redirect_url": payment.confirmation_url})
                    return redirect(payment.confirmation_url)

            success_url = reverse("orders:order_success", args=[order.pk])
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                from django.http import JsonResponse
                return JsonResponse({"redirect_url": success_url})
            return redirect(success_url)
        except ValueError as e:
            import logging as _log
            _log.getLogger(__name__).error(f"CHECKOUT ValueError: {e}")
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                from django.http import JsonResponse
                return JsonResponse({"error": str(e)}, status=400)
            messages.error(request, str(e))
        except Exception as e:
            import logging, traceback
            logging.getLogger(__name__).error(f"CHECKOUT Exception: {e}\n{traceback.format_exc()}")
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                from django.http import JsonResponse
                return JsonResponse({"error": "Произошла ошибка при оформлении заказа"}, status=500)
            messages.error(request, "Произошла ошибка при оформлении заказа")

    addresses = []
    if request.user.is_authenticated:
        addresses = request.user.addresses.all()
    # Calculate total cart weight for CDEK delivery cost estimation
    total_weight = 0
    if cart:
        for item in cart.items.select_related("variant"):
            w = item.variant.weight if item.variant and item.variant.weight else 300
            total_weight += int(w) * item.qty
    total_weight = max(total_weight, 100)
    return render(request, "orders/basket.html", {
        "cart": cart,
        "addresses": addresses,
        "total_weight": total_weight,
        "default_delivery_type": default_delivery_type,
        "recurring_payments_enabled": recurring_enabled,
    })



def edit_address(request, address_id):
    import json
    from django.http import JsonResponse
    from apps.users.models import Address
    if request.method != "POST":
        return JsonResponse({"ok": False}, status=405)
    try:
        addr = Address.objects.get(id=address_id, user=request.user)
    except Address.DoesNotExist:
        return JsonResponse({"ok": False}, status=404)
    addr.label = request.POST.get("label", addr.label)
    addr.city = request.POST.get("city", addr.city)
    addr.street = request.POST.get("street", addr.street)
    addr.house = request.POST.get("house", addr.house)
    addr.apartment = request.POST.get("apartment", addr.apartment)
    addr.postal_code = request.POST.get("postal_code", addr.postal_code)
    addr.is_default = request.POST.get("is_default") == "true"
    addr.save()
    return JsonResponse({"ok": True})


def delete_address(request, address_id):
    from django.http import JsonResponse
    from apps.users.models import Address
    if request.method != "POST":
        return JsonResponse({"ok": False}, status=405)
    try:
        addr = Address.objects.get(id=address_id, user=request.user)
        addr.delete()
    except Address.DoesNotExist:
        pass
    return JsonResponse({"ok": True})


def cart_badge(request):
    cart_service = CartService(request)
    cart = cart_service.get_cart()
    return render(request, "orders/partials/cart_badge.html", {"cart": cart})


def compare_badge(request):
    ids = request.session.get("compare_ids", [])
    count = len(ids) if isinstance(ids, list) else 0
    return render(request, "orders/partials/compare_badge.html", {"compare_count": count})


def wishlist_badge(request):
    from .models import Wishlist
    if request.user.is_authenticated:
        count = Wishlist.objects.filter(user=request.user).count()
    else:
        ids = request.session.get("wishlist_ids", [])
        count = len(ids)
    return render(request, "orders/partials/wishlist_badge.html", {"wishlist_count": count})

def mini_cart(request):
    import time
    time.sleep(0.1)  # tiny simulated network delay for realism if needed, maybe not
    cart_service = CartService(request)
    cart = cart_service.get_cart()
    return render(request, "orders/partials/mini_cart.html", {"cart": cart})

def add_to_cart(request):
    if request.method == "POST":
        import json
        data = json.loads(request.body) if request.content_type == "application/json" else request.POST
        variant_id = data.get("variant_id")
        qty = int(data.get("qty", 1))
        if variant_id:
            cart_service = CartService(request)
            cart_service.add(variant_id, qty)  # FIX: actually add item to cart
            if getattr(request, "htmx", False):
                response = HttpResponse(status=204)
                response["HX-Trigger"] = "cartUpdated"
                return response
            if request.content_type == "application/json":
                from django.http import JsonResponse
                cart = cart_service.get_cart()
                return JsonResponse({
                    "ok": True,
                    "total_items": cart.total_items,
                    "total": str(cart.total),
                    "subtotal": str(cart.subtotal),
                })
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                from django.http import JsonResponse
                cart = cart_service.get_cart()
                return JsonResponse({
                    "ok": True,
                    "total_items": cart.total_items,
                    "total": str(cart.total),
                    "subtotal": str(cart.subtotal),
                })
            messages.success(request, "Товар добавлен в корзину")
    return redirect(request.META.get("HTTP_REFERER", "/catalog/"))

def update_cart(request, variant_id):
    if request.method in ["POST", "PATCH"]:
        import json
        if request.content_type == "application/json":
            data = json.loads(request.body)
            qty = int(data.get("qty", 0))
        else:
            qty = int(request.POST.get("qty", 0))
        cart_service = CartService(request)
        cart_service.update(variant_id, qty)
        if getattr(request, "htmx", False):
            response = HttpResponse(status=204)
            response["HX-Trigger"] = "cartUpdated"
            return response
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            from django.http import JsonResponse
            cart = cart_service.get_cart()
            item_total = None
            item_qty = None
            if cart:
                for item in cart.items.all():
                    if item.variant_id == int(variant_id):
                        item_total = str(item.total_price)
                        item_qty = item.qty
                        break
            return JsonResponse({
                "ok": True,
                "total_items": cart.total_items if cart else 0,
                "total": str(cart.total) if cart else "0",
                "subtotal": str(cart.subtotal) if cart else "0",
                "item_total": item_total,
                "item_qty": item_qty,
            })
    return redirect("orders:basket")

def remove_from_cart(request, variant_id):
    if request.method in ["POST", "DELETE"]:
        cart_service = CartService(request)
        cart_service.remove(variant_id)
        if getattr(request, "htmx", False):
            response = HttpResponse(status=200)
            response["HX-Trigger"] = "cartUpdated"
            return response
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            from django.http import JsonResponse
            cart = cart_service.get_cart()
            return JsonResponse({
                "ok": True,
                "total_items": cart.total_items if cart else 0,
                "total": str(cart.total) if cart else "0",
                "subtotal": str(cart.subtotal) if cart else "0",
                "unique_count": cart.items.count() if cart else 0,
            })
    return redirect("orders:basket")

def apply_promo(request):
    if request.method == "POST":
        code = request.POST.get("code", "")
        next_url = request.POST.get("next", "")
        cart_service = CartService(request)
        success, msg = cart_service.apply_promo(code)
        if request.headers.get("HX-Request"):
            return HttpResponse(msg)
        if not success:
            messages.error(request, msg)
        else:
            messages.success(request, msg)
        if next_url:
            return redirect(next_url)
    return redirect("orders:basket")

def order_success(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    if order.user and order.user != request.user:
        return redirect("catalog:index")
    if order.payment_method in (Order.PAYMENT_CARD, Order.PAYMENT_SBP):
        try:
            payment = order.payment
        except Exception:
            payment = None
        if payment and payment.yookassa_id:
            try:
                from apps.payments.services import sync_payment_from_yookassa

                sync_payment_from_yookassa(payment)
                order.refresh_from_db()
            except Exception:
                import logging

                logging.getLogger(__name__).exception(
                    "Could not reconcile payment on return for order #%s", order.pk
                )
    return render(request, "orders/success.html", {"order": order})

def cart_data_json(request):
    from django.http import JsonResponse
    cart_service = CartService(request)
    cart = cart_service.get_cart()
    data = {}
    if cart:
        for item in cart.items.select_related("variant"):
            data[str(item.variant_id)] = item.qty
    return JsonResponse(data)
