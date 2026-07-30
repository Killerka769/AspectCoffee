from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from .cart_service import CartService
from .models import Cart
@receiver(user_logged_in)
def merge_guest_cart_on_login(sender, request, user, **kwargs):
    if not hasattr(request, 'user'):
        request.user = user
    old_session_key = getattr(request, '_guest_session_key', None)
    if old_session_key:
        guest_cart = Cart.objects.filter(session_key=old_session_key, user__isnull=True).first()
        user_cart = Cart.objects.filter(user=user).first()
        if not user_cart:
            user_cart = Cart.objects.create(user=user)
        if guest_cart and guest_cart.pk != user_cart.pk:
            cart_service = CartService(request)
            cart_service._merge_carts(guest_cart, user_cart)
    cart_service = CartService(request, old_session_key=old_session_key)
    cart_service.get_cart()
