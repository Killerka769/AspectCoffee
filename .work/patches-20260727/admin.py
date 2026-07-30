
from django.contrib import admin
from django.contrib import messages
from datetime import timedelta
from django.utils.html import format_html
from django.utils import timezone
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import action
from import_export.admin import ImportExportModelAdmin
from import_export import resources, fields
from .models import (
    Banner, Cart, CartItem, Order, OrderItem, ProductNote, PromoCode, Wishlist,
    RecurringCharge, RecurringOrder,
)


@admin.register(RecurringOrder)
class RecurringOrderAdmin(ModelAdmin):
    list_display = ["pk", "source_order", "user", "status", "interval_weeks", "next_charge_at", "last_charge_at", "updated_at"]
    list_editable = ["status", "interval_weeks", "next_charge_at"]
    list_filter = ["status", "interval_weeks"]
    search_fields = ["source_order__pk", "user__email", "saved_payment_method_id"]
    readonly_fields = ["created_at", "updated_at"]
    fieldsets = (
        ("Настройки автоповтора", {"fields": ("source_order", "user", "status", "interval_weeks")} ),
        ("Способ и расписание списаний", {"fields": ("saved_payment_method_id", "next_charge_at", "last_charge_at")} ),
        ("Диагностика", {"fields": ("last_error", "created_at", "updated_at")} ),
    )

    @action(description="Включить выбранные автоповторы")
    def activate_selected(self, request, queryset):
        activated = 0
        skipped = 0
        now = timezone.now()
        for plan in queryset:
            if not plan.saved_payment_method_id:
                skipped += 1
                continue
            plan.status = RecurringOrder.STATUS_ACTIVE
            if not plan.next_charge_at:
                plan.next_charge_at = now + timedelta(weeks=plan.interval_weeks)
            plan.last_error = ""
            plan.save(update_fields=["status", "next_charge_at", "last_error", "updated_at"])
            activated += 1
        self.message_user(request, f"Включено автоповторов: {activated}.")
        if skipped:
            self.message_user(
                request,
                f"Пропущено без сохранённого способа оплаты: {skipped}.",
                level=messages.WARNING,
            )

    @action(description="Приостановить выбранные автоповторы")
    def pause_selected(self, request, queryset):
        count = queryset.update(status=RecurringOrder.STATUS_PAUSED, updated_at=timezone.now())
        self.message_user(request, f"Приостановлено автоповторов: {count}.")

    @action(description="Отключить выбранные автоповторы")
    def cancel_selected(self, request, queryset):
        count = queryset.update(status=RecurringOrder.STATUS_CANCELLED, next_charge_at=None, updated_at=timezone.now())
        self.message_user(request, f"Отключено автоповторов: {count}.")

    @action(description="Создать и запустить списание сейчас")
    def charge_now(self, request, queryset):
        from apps.payments.tasks import process_recurring_charge

        queued = 0
        skipped = 0
        for plan in queryset:
            if plan.status != RecurringOrder.STATUS_ACTIVE or not plan.saved_payment_method_id:
                skipped += 1
                continue
            charge = RecurringCharge.objects.create(
                recurring_order=plan,
                scheduled_for=timezone.now(),
            )
            process_recurring_charge.delay(charge.pk)
            queued += 1
        self.message_user(request, f"Поставлено в очередь списаний: {queued}.")
        if skipped:
            self.message_user(
                request,
                f"Пропущено неактивных записей или записей без сохранённой карты: {skipped}.",
                level=messages.WARNING,
            )

    actions = ["activate_selected", "pause_selected", "cancel_selected", "charge_now"]


@admin.register(RecurringCharge)
class RecurringChargeAdmin(ModelAdmin):
    list_display = ["pk", "recurring_order", "scheduled_for", "order", "status", "created_at"]
    list_filter = ["status", "scheduled_for"]
    search_fields = ["recurring_order__source_order__pk", "order__pk", "idempotency_key"]
    readonly_fields = ["idempotency_key", "created_at", "updated_at"]
    fieldsets = (
        ("Списание", {"fields": ("recurring_order", "scheduled_for", "status", "order")} ),
        ("Диагностика", {"fields": ("idempotency_key", "error_message", "created_at", "updated_at")} ),
    )

    @action(description="Повторить выбранные ошибочные списания")
    def retry_failed(self, request, queryset):
        from apps.payments.tasks import process_recurring_charge

        queued = 0
        skipped = 0
        for charge in queryset.select_related("recurring_order"):
            if charge.status != RecurringCharge.STATUS_FAILED:
                skipped += 1
                continue
            plan = charge.recurring_order
            if not plan.saved_payment_method_id:
                skipped += 1
                continue
            plan.status = RecurringOrder.STATUS_ACTIVE
            plan.last_error = ""
            plan.save(update_fields=["status", "last_error", "updated_at"])
            charge.status = RecurringCharge.STATUS_PENDING
            charge.error_message = ""
            charge.save(update_fields=["status", "error_message", "updated_at"])
            process_recurring_charge.delay(charge.pk)
            queued += 1
        self.message_user(request, f"Повторно поставлено в очередь: {queued}.")
        if skipped:
            self.message_user(request, f"Пропущено списаний: {skipped}.", level=messages.WARNING)

    actions = ["retry_failed"]

class OrderResource(resources.ModelResource):
    class Meta:
        model = Order
        fields = ["id", "status", "delivery_type", "payment_method", "payment_status",
                   "total_amount", "discount_amount", "contact_name", "contact_phone",
                   "contact_email", "cdek_track_number", "created_at"]
        export_order = fields
class CartItemInline(TabularInline):
    model = CartItem
    extra = 0
    raw_id_fields = ["variant"]
    readonly_fields = ["line_total"]
    @admin.display(description="Сумма")
    def line_total(self, obj):
        return f"{obj.total_price} ₽"
class OrderItemInline(TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ["product_name", "variant_description", "qty", "price_at_order", "line_total"]
    fields = ["product_name", "variant_description", "qty", "price_at_order", "line_total"]

    @admin.display(description="Сумма")
    def line_total(self, obj):
        return f"{obj.total_price} ₽"
STATUS_COLORS = {
    "new": "#71717a",
    "paid": "#16a34a",
    "assembling": "#ca8a04",
    "shipped": "#2563eb",
    "delivered": "#9333ea",
    "completed": "#0d9488",
    "cancelled": "#dc2626",
}
@admin.register(Order)
class OrderAdmin(ImportExportModelAdmin, ModelAdmin):
    resource_classes = [OrderResource]
    list_display = [
        "pk", "colored_status", "user", "recipient_display",
        "contact_phone", "delivery_type", "payment_method",
        "payment_status", "total_amount", "cdek_track_number", "created_at",
    ]
    list_editable = ["cdek_track_number"]
    list_filter = ["status", "delivery_type", "payment_method", "payment_status", "created_at"]
    search_fields = ["pk", "contact_name", "contact_phone", "contact_email", "cdek_track_number"]
    readonly_fields = [
        "created_at", "updated_at", "total_amount", "discount_amount",
        "payment_id", "repeat_order_available",
    ]
    inlines = [OrderItemInline]
    date_hierarchy = "created_at"
    ordering = ["-created_at"]
    fieldsets = (
        ("Основное", {"fields": ("status", "user", "comment", "created_at", "updated_at")}),
        ("Контакты", {"fields": ("contact_name", "contact_phone", "contact_email", "phone_code")}),
        ("Получатель", {"fields": ("recipient_name", "recipient_phone")}),
        ("Повтор заказа", {"fields": ("repeat_order_available",)}),
        ("Организация", {"fields": ("is_organization", "org_name", "org_inn")}),
        ("Доставка", {"fields": ("delivery_type", "delivery_address", "delivery_cost", "cdek_track_number", "cdek_order_uuid")}),
        ("Оплата", {"fields": ("payment_method", "payment_status", "payment_id")}),
        ("Суммы", {"fields": ("promo_code", "discount_amount", "total_amount")}),
    )
    def colored_status(self, obj):
        color = STATUS_COLORS.get(obj.status, "#71717a")
        return format_html(
            '<span style="background:{};color:white;padding:3px 10px;border-radius:12px;font-size:12px">{}</span>',
            color, obj.get_status_display(),
        )
    colored_status.short_description = "Статус"

    @admin.display(description="Получатель")
    def recipient_display(self, obj):
        return obj.delivery_recipient_name or "—"

    @admin.display(description="Повторить заказ")
    def repeat_order_available(self, obj):
        if not obj or not obj.user_id:
            return "Недоступно: заказ без учетной записи"
        return format_html(
            "Доступно. В списке заказов выберите заказ и примените действие "
            "<b>«Повторить заказ в корзину покупателя»</b>."
        )

    def save_model(self, request, obj, form, change):
        previous_status = None
        if change and obj.pk:
            previous_status = (
                Order.objects.filter(pk=obj.pk)
                .values_list("status", flat=True)
                .first()
            )

        super().save_model(request, obj, form, change)

        if change and previous_status != obj.status:
            try:
                from .tasks import send_order_status_email
                send_order_status_email.delay(obj.id, obj.status)
            except Exception:
                pass

    @action(description="Отметить как оплачено и уведомить покупателя")
    def mark_paid(self, request, queryset):
        for order in queryset:
            order.status = Order.STATUS_PAID
            order.payment_status = Order.PAYMENT_STATUS_PAID
            order.save(update_fields=["status", "payment_status"])
            try:
                from .tasks import send_order_status_email
                send_order_status_email.delay(order.id, Order.STATUS_PAID)
            except Exception:
                pass
        self.message_user(request, f"{queryset.count()} заказов отмечены как оплаченные")

    @action(description="Передать в сборку и уведомить")
    def mark_assembling(self, request, queryset):
        for order in queryset:
            order.status = Order.STATUS_ASSEMBLING
            order.save(update_fields=["status"])
            try:
                from .tasks import send_order_status_email
                send_order_status_email.delay(order.id, Order.STATUS_ASSEMBLING)
            except Exception:
                pass
        self.message_user(request, f"{queryset.count()} заказов в сборке")

    @action(description="Передать в доставку и уведомить")
    def mark_shipped(self, request, queryset):
        for order in queryset:
            order.status = Order.STATUS_SHIPPED
            order.save(update_fields=["status"])
            try:
                from .tasks import send_order_status_email
                send_order_status_email.delay(order.id, Order.STATUS_SHIPPED)
            except Exception:
                pass
        self.message_user(request, f"{queryset.count()} заказов переданы в доставку")

    @action(description="Отметить как доставленные и уведомить")
    def mark_delivered(self, request, queryset):
        for order in queryset:
            order.status = Order.STATUS_DELIVERED
            order.save(update_fields=["status"])
            try:
                from .tasks import send_order_status_email
                send_order_status_email.delay(order.id, Order.STATUS_DELIVERED)
            except Exception:
                pass
        self.message_user(request, f"{queryset.count()} заказов доставлены")

    @action(description="Завершить заказы и уведомить")
    def mark_completed(self, request, queryset):
        for order in queryset:
            order.status = Order.STATUS_COMPLETED
            order.save(update_fields=["status"])
            try:
                from .tasks import send_order_status_email
                send_order_status_email.delay(order.id, Order.STATUS_COMPLETED)
            except Exception:
                pass
        self.message_user(request, f"{queryset.count()} заказов завершены")

    @action(description="Отменить заказы и уведомить")
    def mark_cancelled(self, request, queryset):
        for order in queryset:
            order.status = Order.STATUS_CANCELLED
            order.save(update_fields=["status"])
            try:
                from .tasks import send_order_status_email
                send_order_status_email.delay(order.id, Order.STATUS_CANCELLED)
            except Exception:
                pass
        self.message_user(request, f"{queryset.count()} заказов отменены")

    @action(description="Сгенерировать инвойс (PDF)")
    def generate_invoice(self, request, queryset):
        from .utils import generate_wholesale_invoice_pdf
        from django.http import HttpResponse
        if queryset.count() != 1:
            self.message_user(request, "Выберите ровно 1 заказ для генерации инвойса")
            return
        order = queryset.first()
        buffer = generate_wholesale_invoice_pdf(order)
        response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="invoice_{order.pk}.pdf"'
        return response

    @action(description="Повторить заказ в корзину покупателя")
    def repeat_in_customer_cart(self, request, queryset):
        from apps.orders.reorder import add_order_items_to_user_cart

        repeated = 0
        skipped_orders = 0
        skipped_items = []
        for order in queryset.select_related("user"):
            if not order.user_id:
                skipped_orders += 1
                continue
            result = add_order_items_to_user_cart(order, order.user)
            if result["added"]:
                repeated += 1
            skipped_items.extend(result["skipped"])
        message = f"Заказов добавлено в корзины покупателей: {repeated}."
        if skipped_orders:
            message += f" Без учетной записи пропущено: {skipped_orders}."
        if skipped_items:
            message += f" Недоступных позиций пропущено: {len(skipped_items)}."
        self.message_user(request, message)

    actions = ["mark_paid", "mark_assembling", "mark_shipped", "mark_delivered", "mark_completed", "mark_cancelled", "generate_invoice", "repeat_in_customer_cart"]
@admin.register(PromoCode)
class PromoCodeAdmin(ModelAdmin):
    list_display = ["code", "discount_type", "discount_value", "valid_from", "valid_to", "used_count", "usage_limit", "is_active"]
    list_editable = ["is_active"]
    list_filter = ["discount_type", "is_active"]
    search_fields = ["code"]
    readonly_fields = ["used_count"]
@admin.register(Banner)
class BannerAdmin(ModelAdmin):
    list_display = ["title", "is_active", "show_from", "show_to", "order"]
    list_editable = ["is_active", "order"]
    search_fields = ["title"]
@admin.register(Cart)
class CartAdmin(ModelAdmin):
    list_display = ["id", "user", "session_key_short", "total_display", "total_items_display", "updated_at"]
    list_filter = ["updated_at"]
    search_fields = ["user__email", "session_key"]
    readonly_fields = ["created_at", "updated_at", "total_display", "total_items_display"]
    raw_id_fields = ["user", "promo_code"]
    inlines = [CartItemInline]
    fieldsets = (
        (None, {"fields": ("user", "session_key", "promo_code")}),
        ("Итоги", {"fields": ("total_items_display", "total_display", "created_at", "updated_at")}),
    )
    @admin.display(description="Сессия")
    def session_key_short(self, obj):
        if not obj.session_key:
            return "—"
        s = obj.session_key
        return f"{s[:8]}…" if len(s) > 10 else s
    @admin.display(description="Позиций")
    def total_items_display(self, obj):
        return obj.total_items
    @admin.display(description="Сумма")
    def total_display(self, obj):
        return f"{obj.total} ₽"
@admin.register(Wishlist)
class WishlistAdmin(ModelAdmin):
    list_display = ["user", "product", "added_at"]
    list_filter = ["added_at"]
    search_fields = ["user__email", "product__name"]
    raw_id_fields = ["user", "product"]
@admin.register(OrderItem)
class OrderItemAdmin(ModelAdmin):
    list_display = ["order", "product_name", "variant_description", "qty", "price_at_order", "line_total"]
    list_filter = ["order__status"]
    search_fields = ["product_name", "order__pk"]
    readonly_fields = ["order", "variant", "product_name", "variant_description", "qty", "price_at_order"]
    ordering = ["-order__id"]
    @admin.display(description="Сумма строки")
    def line_total(self, obj):
        return f"{obj.total_price} ₽"
    def has_add_permission(self, request):
        return False


@admin.register(ProductNote)
class ProductNoteAdmin(ModelAdmin):
    list_display = ["user", "product", "text_preview", "updated_at"]
    list_filter = ["created_at", "updated_at"]
    search_fields = ["user__email", "product__name", "text"]
    autocomplete_fields = ["user", "product"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["-updated_at"]

    @admin.display(description="Заметка")
    def text_preview(self, obj):
        return obj.text[:100]
