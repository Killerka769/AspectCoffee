from apps.orders.models import Cart


def get_loyalty_discount(user):
    """Compute loyalty discount % from all non-cancelled orders."""
    from django.db.models import Sum
    from apps.orders.models import Order
    from apps.users.models import DiscountLevel
    if not user.is_authenticated:
        return 0
    total_spent = (
        Order.objects.filter(user=user)
        .exclude(status=Order.STATUS_CANCELLED)
        .aggregate(t=Sum("total_amount"))["t"]
        or 0
    )
    levels = list(DiscountLevel.objects.filter(is_active=True).order_by("min_amount"))
    discount = 0
    for level in levels:
        if total_spent >= level.min_amount:
            discount = level.discount_percent
        else:
            break
    return discount


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
            # The header shows the value of goods in the cart. Discounts are
            # displayed separately in the basket and must not silently change
            # the price next to the cart icon.
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
