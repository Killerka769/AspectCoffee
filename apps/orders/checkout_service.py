import logging
from decimal import Decimal, InvalidOperation
from django.db import transaction
from django.conf import settings
from apps.users.models import User, BonusTransaction, Address
from apps.orders.models import Order, OrderItem, Cart

class CheckoutService:
    def __init__(self, request):
        self.request = request
        self.user = request.user
        self.session_key = request.session.session_key

    def get_checkout_data(self):
        if self.user.is_authenticated:
            cart = Cart.objects.filter(user=self.user).first()
        else:
            cart = Cart.objects.filter(session_key=self.session_key).first()

        if not cart or cart.items.count() == 0:
            return None

        addresses = []
        if self.user.is_authenticated:
            addresses = self.user.addresses.all()

        return {
            'cart': cart,
            'addresses': addresses,
            'user': self.user
        }

    @transaction.atomic
    def place_order(self, data, order_user=None):
        if data.get("payment_method") == Order.PAYMENT_COD and not settings.PAYMENT_COD_ENABLED:
            raise ValueError("Оплата при получении недоступна")
        if self.user.is_authenticated:
            cart = Cart.objects.get(user=self.user)
        else:
            cart = Cart.objects.get(session_key=self.session_key)

        if cart.items.count() == 0:
            raise ValueError("Корзина пуста")

        resolved_order_user = order_user
        if resolved_order_user is None and self.user.is_authenticated:
            resolved_order_user = self.user

        # Update user profile if authenticated
        if resolved_order_user is not None:
            resolved_order_user.first_name = data.get("first_name", "")
            resolved_order_user.last_name = data.get("last_name", "")
            resolved_order_user.phone = data.get("phone", "")
            resolved_order_user.email = data.get("email", "")
            if data.get("city"):
                resolved_order_user.city = data.get("city")
            resolved_order_user.save()

        try:
            delivery_cost = Decimal(str(data.get("cdek_delivery_cost", 0) or 0))
        except (InvalidOperation, TypeError, ValueError):
            raise ValueError("Не удалось определить стоимость доставки")
        if delivery_cost < 0:
            raise ValueError("Некорректная стоимость доставки")
        order_total = cart.total + delivery_cost

        # Handle Internal Payment
        if data.get("payment_method") == "internal":
            if not self.user.is_authenticated:
                raise ValueError("Оплата внутренним счетом доступна только для авторизованных пользователей")
            payment_user = User.objects.select_for_update().get(pk=self.user.pk)
            if payment_user.balance < order_total:
                raise ValueError(f"Недостаточно средств на балансе. Ваш баланс: {payment_user.balance} ₽")

            # Deduct from balance
            payment_user.balance -= order_total
            payment_user.save(update_fields=["balance"])
            self.user.balance = payment_user.balance

            # Create transaction record
            BonusTransaction.objects.create(
                user=payment_user,
                amount=-int(order_total),
                type=BonusTransaction.TYPE_SPEND,
                description=f"Оплата заказа"
            )

        if data["delivery_type"] == "cdek_pvz" and not data.get("cdek_pvz_code"):
             raise ValueError("Пожалуйста, выберите пункт выдачи СДЭК на карте")

        order = Order(
            user=resolved_order_user,
            delivery_type=data["delivery_type"],
            payment_method=data["payment_method"],
            promo_code=cart.promo_code,
            discount_amount=cart.discount_amount,
            total_amount=order_total,
            contact_name=f"{data.get('first_name', '')} {data.get('last_name', '')}",
            contact_phone=data.get('phone', ''),
            contact_email=data.get('email', ''),
            comment=data.get('comment', ''),
            phone_code=data.get('phone_code', '+7'),
            is_organization=data.get('is_organization') == 'on' or data.get('is_organization') is True,
            org_name=data.get('org_name', ''),
            org_inn=data.get('org_inn', ''),
            recipient_name=data.get('recipient_name', ''),
            recipient_phone=data.get('recipient_phone', ''),
            delivery_address={
                'city': data.get('city', ''),
                'street': data.get('street', ''),
                'house': data.get('house', ''),
                'apartment': data.get('apartment', ''),
                'postal_code': data.get('postal_code', '')
            },
            cdek_pvz_code=data.get('cdek_pvz_code', ''),
            cdek_pvz_address=data.get('cdek_pvz_address', ''),
            delivery_cost=delivery_cost
        )

        # If paid internally, mark order as paid
        if data.get("payment_method") == "internal":
            order.payment_status = "paid"
            order.status = "paid"

        order.save()

        for item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                variant=item.variant,
                product_name=item.variant.product.name,
                variant_description=", ".join(
                    p for p in [
                        f"{item.variant.weight}г",
                        item.variant.get_grind_display(),
                        item.variant.roast_display,
                    ] if p
                ),
                qty=item.qty,
                price_at_order=item.variant.effective_price or item.variant.price
            )

        if cart.promo_code:
            cart.promo_code.used_count += 1
            cart.promo_code.save()

        cart.items.all().delete()
        cart.promo_code = None
        cart.save()

        return order
