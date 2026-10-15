from apps.orders.models import Cart


def get_loyalty_discount(user):
    """Return the user's fixed personal discount (assigned in admin).

    The previous cumulative DiscountLevel model was removed. Fixed discount
    is stored on User.wholesale_discount and applies to every order.
    """
    if not user.is_authenticated:
        return 0
    return user.wholesale_discount or 0


def cart_context(request):
    """Provide mini-cart data (item count + total) to every template."""
    total_items = 0
    total = 0
    cart_promo_code = None
    cart = None

    cart_variant_ids = {}
    try:
        if request.user.is_authenticated:
            cart = Cart.objects.filter(user=request.user).first()
        else:
            session_key = getattr(request.session, "session_key", None)
            cart = (
                Cart.objects.filter(session_key=session_key, user=None).first()
                if session_key
                else None
            )

        if cart:
            total_items = cart.total_items
            total = cart.subtotal
            if cart.promo_code_id:
                cart_promo_code = cart.promo_code.code
            for item in cart.items.select_related('variant').all():
                cart_variant_ids[str(item.variant_id)] = item.qty
    except Exception:
        pass

    wishlist_ids = []
    wishlist_count = 0
    loyalty_discount = 0
    notif_unread_count = 0
    if request.user.is_authenticated:
        from apps.orders.models import Wishlist
        wishlist_items = list(Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True))
        wishlist_ids = wishlist_items
        wishlist_count = len(wishlist_items)
        loyalty_discount = get_loyalty_discount(request.user)

        from apps.users.models import UserNotification
        notif_unread_count = UserNotification.objects.filter(
            user=request.user,
            is_read=False,
        ).count()

    return {
        "cart_total_items": total_items,
        "cart_total": total,
        "cart_promo_code": cart_promo_code,
        "cart_variant_ids": cart_variant_ids,
        "wishlist_ids": wishlist_ids,
        "wishlist_count": wishlist_count,
        "loyalty_discount": loyalty_discount,
        "notif_unread_count": notif_unread_count,
    }