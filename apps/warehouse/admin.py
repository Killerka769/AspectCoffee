from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import StockItem


@admin.register(StockItem)
class StockItemAdmin(ModelAdmin):
    list_display = ["variant", "qty", "min_qty", "low_stock", "updated_at"]
    list_filter = ["updated_at"]
    search_fields = ["variant__product__name", "variant__sku"]
    raw_id_fields = ["variant"]
    list_editable = ["qty", "min_qty"]
    readonly_fields = ["updated_at", "last_low_stock_notification"]
    ordering = ["qty", "variant__product__name"]

    @admin.display(description="Низкий остаток", boolean=True)
    def low_stock(self, obj):
        return obj.is_low
