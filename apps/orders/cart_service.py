from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Prefetch
from apps.orders.models import Cart, CartItem, PromoCode
from apps.catalog.models import ProductVariant
class CartService:
    def __init__(self, request, old_session_key=None):
        self.request = request
        self.session = request.session
        self.user = request.user
        self.old_session_key = old_session_key
        if not self.session.session_key:
            self.session.create()
    def get_cart(self):
        if self.user.is_authenticated:
            cart = Cart.objects.filter(user=self.user).first()
            if not cart:
                cart = Cart.objects.create(user=self.user)
            guest_carts = Cart.objects.filter(session_key=self.session.session_key)
            if self.old_session_key and self.old_session_key != self.session.session_key:
                guest_carts = guest_carts | Cart.objects.filter(session_key=self.old_session_key)
            guest_carts = guest_carts.exclude(pk=cart.pk)
            for guest_cart in guest_carts:
                if guest_cart != cart:
                    self._merge_carts(guest_cart, cart)
        else:
            cart = Cart.objects.filter(session_key=self.session.session_key).first()
            if not cart:
                cart = Cart.objects.create(session_key=self.session.session_key)
            duplicates = Cart.objects.filter(session_key=self.session.session_key).exclude(id=cart.id)
            for dup in duplicates:
                self._merge_carts(dup, cart)
        qs = Cart.objects.filter(pk=cart.pk).select_related(
            "user", "promo_code"
        ).prefetch_related(
            Prefetch(
                "items",
                queryset=CartItem.objects.select_related("variant", "variant__product"),
            )
        )
        return qs.first()
    def _merge_carts(self, guest_cart, user_cart):
        for guest_item in guest_cart.items.all():
            user_item, created = CartItem.objects.get_or_create(
                cart=user_cart,
                variant=guest_item.variant,
                defaults={'qty': guest_item.qty}
            )
            if not created:
                user_item.qty += guest_item.qty
                user_item.save()
        guest_cart.delete()
    def add(self, variant_id, qty=1):
        cart = self.get_cart()
        variant = ProductVariant.objects.get(id=variant_id)
        item, created = CartItem.objects.get_or_create(
            cart=cart, variant=variant,
            defaults={'qty': qty}
        )
        if not created:
            item.qty = qty
            item.save()
        return cart
    def update(self, variant_id, qty):
        cart = self.get_cart()
        qty = int(qty)
        if qty <= 0:
            self.remove(variant_id)
        else:
            try:
                item = CartItem.objects.get(cart=cart, variant_id=variant_id)
                item.qty = qty
                item.save()
            except ObjectDoesNotExist:
                pass
        return cart
    def remove(self, variant_id):
        cart = self.get_cart()
        CartItem.objects.filter(cart=cart, variant_id=variant_id).delete()
        return cart
    def apply_promo(self, code):
        cart = self.get_cart()
        try:
            promo = PromoCode.objects.get(code__iexact=code, is_active=True)
            if promo.is_valid() and cart.subtotal >= promo.min_order_amount:
                cart.promo_code = promo
                cart.save()
                return True, "Промо-код применён"
            else:
                cart.promo_code = None
                cart.save()
                return False, "Промо-код недействителен или не выполнены условия"
        except PromoCode.DoesNotExist:
            cart.promo_code = None
            cart.save()
            return False, "Промо-код не найден"
    def remove_promo(self):
        cart = self.get_cart()
        cart.promo_code = None
        cart.save()
        return cart
    def clear(self):
        cart = self.get_cart()
        cart.items.all().delete()
        cart.promo_code = None
        cart.save()
