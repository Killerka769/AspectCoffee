from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from .models import Payment


STATUS_COLORS = {
    "pending": "#71717a",
    "succeeded": "#16a34a",
    "cancelled": "#dc2626",
    "refunded": "#ca8a04",
}


@admin.register(Payment)
class PaymentAdmin(ModelAdmin):
    list_display = [
        "pk", "order_link", "colored_status", "amount_display",
        "yookassa_id", "created_at",
    ]
    list_filter = ["status", "created_at"]
    search_fields = ["yookassa_id", "order__pk", "order__contact_name", "order__contact_email"]
    readonly_fields = [
        "yookassa_id", "yookassa_refund_id", "amount", "confirmation_url",
        "saved_payment_method_id", "payment_method_saved", "payment_method_type", "card_last4",
        "created_at", "updated_at", "order",
    ]
    ordering = ["-created_at"]
    date_hierarchy = "created_at"
    fieldsets = (
        ("\u041e\u0441\u043d\u043e\u0432\u043d\u043e\u0435", {"fields": ("order", "status", "amount", "created_at", "updated_at")}),
        ("\u042eKassa", {"fields": ("yookassa_id", "yookassa_refund_id", "confirmation_url", "saved_payment_method_id", "payment_method_saved", "payment_method_type", "card_last4")}),
    )

    @admin.display(description="\u0421\u0442\u0430\u0442\u0443\u0441")
    def colored_status(self, obj):
        color = STATUS_COLORS.get(obj.status, "#71717a")
        return format_html(
            '<span style="background:{};color:white;padding:3px 10px;border-radius:12px;font-size:12px">{}</span>',
            color, obj.get_status_display(),
        )

    @admin.display(description="\u0421\u0443\u043c\u043c\u0430")
    def amount_display(self, obj):
        return f"{obj.amount} \u20bd"

    @admin.display(description="\u0417\u0430\u043a\u0430\u0437")
    def order_link(self, obj):
        if obj.order_id:
            from django.urls import reverse
            url = reverse("admin:orders_order_change", args=[obj.order_id])
            return format_html('<a href="{}">\u0417\u0430\u043a\u0430\u0437 #{}</a>', url, obj.order_id)
        return "\u2014"
