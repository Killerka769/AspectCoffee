
import functools
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import FileResponse
from django.utils.decorators import method_decorator
from django.views import View

from apps.orders.models import Order
from apps.warehouse.models import StockItem


def warehouse_required(view_func):
    """Allow only warehouse_operator role (or staff)."""
    @functools.wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        from apps.users.models import User
        if not (
            request.user.role == User.ROLE_WAREHOUSE
            or request.user.is_staff
        ):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return _wrapped


@warehouse_required
def assembly_queue(request):
    """List of orders with status 'assembling' — warehouse operator's main view."""
    orders = (
        Order.objects.filter(status=Order.STATUS_ASSEMBLING)
        .prefetch_related("items__variant__product")
        .order_by("created_at")
    )
    return render(request, "warehouse/queue.html", {"orders": orders})


@warehouse_required
def order_detail(request, pk):
    """Single order detail for warehouse operator."""
    order = get_object_or_404(
        Order.objects.prefetch_related("items__variant__product"),
        pk=pk,
        status=Order.STATUS_ASSEMBLING,
    )
    return render(request, "warehouse/order_detail.html", {"order": order})


@warehouse_required
def mark_assembled(request, pk):
    """Mark order as shipped (assembled) and notify manager."""
    if request.method != "POST":
        return redirect("warehouse:queue")

    order = get_object_or_404(Order, pk=pk, status=Order.STATUS_ASSEMBLING)
    order.status = Order.STATUS_SHIPPED
    order.save(update_fields=["status"])

    from apps.orders.tasks import create_cdek_waybill, send_order_status_email
    try:
        create_cdek_waybill.delay(order.id)
        send_order_status_email.delay(order.id, Order.STATUS_SHIPPED)
    except Exception:
        pass

    messages.success(request, f"Заказ #{pk} помечен как «Передан в СДЭК»")
    return redirect("warehouse:queue")


@warehouse_required
def packing_slip_pdf(request, pk):
    """Generate and return packing slip PDF for an order."""
    order = get_object_or_404(
        Order.objects.prefetch_related("items__variant__product"),
        pk=pk,
    )
    from apps.warehouse.utils import generate_packing_slip_pdf
    buffer = generate_packing_slip_pdf(order)
    return FileResponse(
        buffer,
        as_attachment=True,
        filename=f"packing_slip_{pk}.pdf",
        content_type="application/pdf",
    )


@warehouse_required
def stock_table(request):
    """Warehouse stock levels view with manual inventory update."""
    items = StockItem.objects.select_related("variant__product").order_by(
        "variant__product__name", "variant"
    )
    if request.method == "POST":
        item_id = request.POST.get("item_id")
        new_qty = request.POST.get("qty")
        if item_id and new_qty is not None:
            try:
                stock = StockItem.objects.get(pk=item_id)
                stock.qty = int(new_qty)
                stock.save(update_fields=["qty"])  # only qty — signal checks update_fields
                messages.success(request, f"Остаток обновлён: {stock.variant} — {stock.qty} шт.")
            except (StockItem.DoesNotExist, ValueError):
                messages.error(request, "Ошибка при обновлении остатка")
        return redirect("warehouse:stock")
    return render(request, "warehouse/stock.html", {"items": items})
