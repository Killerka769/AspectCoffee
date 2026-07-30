from .models import Cart, CartItem


def add_order_items_to_user_cart(order, user):
    """Copy all currently available order items into the user's cart."""
    cart, _ = Cart.objects.get_or_create(user=user)
    skipped = []
    added = 0

    for item in order.items.select_related("variant").all():
        variant = item.variant
        if variant is None:
            skipped.append(item.product_name)
            continue
        stock = getattr(variant, "stock", None)
        if stock and stock.qty < 1:
            skipped.append(item.product_name)
            continue
        if not getattr(variant, "is_available", True):
            skipped.append(item.product_name)
            continue

        cart_item, created = CartItem.objects.get_or_create(cart=cart, variant=variant)
        if created:
            cart_item.qty = item.qty
        else:
            cart_item.qty += item.qty
        cart_item.save(update_fields=["qty"])
        added += 1

    return {"cart": cart, "added": added, "skipped": skipped}
