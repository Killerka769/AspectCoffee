
from django import forms
from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import action
from import_export.admin import ImportExportModelAdmin
from .models import (
    Category, FlavorNote, BrewMethod,
    Product, ProductVariant, ProductImage,
    Review,
    SiteSettings, CatalogFilterSettings,
    GrindType, RoastType, ProductPackaging, Cafe,
    NavMenuItem, PromoSlide,
)
from apps.pages.models import ReviewComment

@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ["name", "parent", "is_active", "is_featured", "order", "slug"]
    list_editable = ["is_active", "is_featured", "order"]
    list_filter = ["is_active", "is_featured", "parent"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}
    fieldsets = (
        (None, {"fields": ("name", "h1", "slug", "parent", "description", "image", "is_active", "is_featured", "order")}),
        ("SEO", {"fields": ("seo_title", "seo_description"), "classes": ("collapse",)}),
    )
    def view_on_site(self, obj):
        return obj.get_absolute_url()


class ProductAdminForm(forms.ModelForm):
    """Universal required fields; section-specific product data stays optional."""

    class Meta:
        model = Product
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["description"].required = True
        self.fields["main_image"].required = True
        self.fields["description"].help_text = (
            "Обязательное общее описание товара для всех разделов каталога."
        )
        self.fields["main_image"].help_text = (
            "Обязательное основное изображение товара для карточки и страницы товара."
        )


class ProductPackagingInline(TabularInline):
    model = ProductPackaging
    extra = 0
    fields = ["weight", "price", "old_price", "order", "is_active"]
    ordering = ["order", "weight"]


class ProductVariantInline(TabularInline):
    model = ProductVariant
    extra = 0
    # Для товара без фасовки цена хранится непосредственно в варианте.
    fields = [
        "packaging", "price", "old_price", "grind_type", "roast_type",
        "stock_qty", "sku", "is_preorder",
    ]
    show_change_link = True
class ProductImageInline(TabularInline):
    model = ProductImage
    extra = 1
    fields = ["image", "alt", "order"]
    readonly_fields = ["image_preview"]
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height:60px" />', obj.image.url)
        return "—"
    image_preview.short_description = "Превью"
@admin.register(Product)
class ProductAdmin(ImportExportModelAdmin, ModelAdmin):
    form = ProductAdminForm
    list_display = ["name", "category", "roast_level", "in_stock", "is_active", "is_featured", "rating_avg"]
    list_editable = ["is_active", "is_featured", "in_stock"]
    list_filter = ["category", "roast_level", "in_stock", "is_active", "is_featured", "is_new", "is_bestseller", "is_microlot"]
    search_fields = ["name", "slug", "description", "origin_country"]
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ["flavor_notes", "brew_methods", "related_products"]
    inlines = [ProductPackagingInline, ProductVariantInline, ProductImageInline]
    readonly_fields = ["rating_avg", "reviews_count", "created_at", "updated_at"]
    fieldsets = (
        (
            "Основное",
            {
                "fields": ("name", "slug", "category", "description", "short_description", "main_image"),
                "description": "Общие данные для любого товара: название, описание, категория и изображение.",
            },
        ),
        (
            "Контентные табы на фронте (необязательно)",
            {
                "fields": ("storage_description", "delivery_description"),
                "description": "Пустые вкладки не выводятся на сайте.",
            },
        ),
        (
            "Атрибуты кофе (необязательно)",
            {
                "classes": ("collapse",),
                "fields": (
                    "roast_level", "processing_method", "origin_country", "region",
                    "altitude", "q_score", "harvest_year", "variety", "caffeine_content",
                    "composition", "brew_methods", "flavor_notes",
                ),
                "description": "Заполняйте только для кофе; пустые поля на сайте не показываются.",
            },
        ),
        (
            "Профиль вкуса (необязательно)",
            {
                "classes": ("collapse",),
                "fields": ("body", "acidity", "sweetness", "flavor_description_html"),
            },
        ),
        ("Флаги", {"fields": ("is_active", "is_featured", "is_new", "is_bestseller", "is_microlot", "in_stock")}),
        ("Похожие товары", {"fields": ("related_products",), "classes": ("collapse",)}),
        ("Статистика", {"fields": ("rating_avg", "reviews_count", "created_at", "updated_at"), "classes": ("collapse",)}),
        ("SEO", {"fields": ("seo_title", "seo_description"), "classes": ("collapse",)}),
    )
    @action(description="Активировать выбранные товары")
    def make_active(self, request, queryset):
        queryset.update(is_active=True)
    @action(description="Снять с публикации")
    def make_inactive(self, request, queryset):
        queryset.update(is_active=False)
    def view_on_site(self, obj):
        return obj.get_absolute_url()
    class Media:
        css = {"all": ("asset/css/admin_aspect.css",)}

class ReviewCommentInline(TabularInline):
    model = ReviewComment
    extra = 0
    fields = ["user", "parent", "text", "is_approved", "created_at"]
    readonly_fields = ["created_at"]


@admin.register(Review)
class ReviewAdmin(ModelAdmin):
    list_display = ["product", "author_name", "user", "rating", "delivery_rating", "status", "created_at"]
    list_editable = ["status"]
    list_filter = ["status", "rating"]
    search_fields = ["product__name", "text", "author_name"]
    readonly_fields = ["created_at", "is_approved"]
    inlines = [ReviewCommentInline]
    def save_model(self, request, obj, form, change):
        old_status = None
        if change:
            from apps.catalog.models import Review
            old_status = Review.objects.filter(pk=obj.pk).values_list("status", flat=True).first()
        super().save_model(request, obj, form, change)
        if old_status and old_status != obj.status:
            from apps.catalog.signals import recompute_product_reviews
            recompute_product_reviews(obj.product_id)
    @action(description="Опубликовать выбранные отзывы")
    def approve_reviews(self, request, queryset):
        from apps.catalog.models import Review
        product_ids = set()
        published = 0
        for review in queryset.exclude(status=Review.STATUS_PUBLISHED):
            product_ids.add(review.product_id)
            review.status = Review.STATUS_PUBLISHED
            review.save(update_fields=["status", "is_approved"])
            published += 1
        from .signals import recompute_product_reviews
        for pid in product_ids:
            recompute_product_reviews(pid)
        self.message_user(request, f"Опубликовано отзывов: {published}")
    @action(description="Отклонить выбранные отзывы")
    def reject_reviews(self, request, queryset):
        from apps.catalog.models import Review
        product_ids = set()
        rejected = 0
        for review in queryset.exclude(status=Review.STATUS_UNPUBLISHED):
            product_ids.add(review.product_id)
            review.status = Review.STATUS_UNPUBLISHED
            review.save(update_fields=["status", "is_approved"])
            rejected += 1
        from .signals import recompute_product_reviews
        for pid in product_ids:
            recompute_product_reviews(pid)
        self.message_user(request, f"Отклонено отзывов: {rejected}")

@admin.register(FlavorNote)
class FlavorNoteAdmin(ModelAdmin):
    list_display = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ["name", "slug"]
@admin.register(BrewMethod)
class BrewMethodAdmin(ModelAdmin):
    list_display = ["name", "slug", "guide_url"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(SiteSettings)
class SiteSettingsAdmin(ModelAdmin):
    fieldsets = (
        ("Основное", {"fields": ("site_name",)}),
        ("Ссылки и контакты", {"fields": ("contact_phone", "contact_email", "contact_telegram", "contact_whatsapp", "free_delivery_min")}),
        ("Корзина и оформление", {"fields": ("cart_guarantee_text", "repeat_order_text", "payment_timeout_minutes", "success_title", "success_message", "success_footer")}),
        ("Автоплатежи", {
            "fields": ("recurring_payments_enabled",),
            "description": "Глобальное управление повторными заказами и автоматическими списаниями с сохранённых карт.",
        }),
        ("Способы доставки", {
            "fields": (
                "enable_city_courier",
                "enable_pickup",
                "enable_cdek_pvz",
                "enable_cdek_door",
            ),
            "description": "Включённые варианты отображаются в корзине и принимаются сервером. Для работы без собственной доставки оставьте только варианты СДЭК.",
        }),
        ("Шаблонные описания", {"fields": ("default_storage_description", "default_delivery_description")}),
    )

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False




@admin.register(CatalogFilterSettings)
class CatalogFilterSettingsAdmin(ModelAdmin):
    """1.6 — управляемые пороги ситуативных фильтров каталога (singleton)."""
    fieldsets = (
        ("Сортировка по умолчанию", {"fields": ("default_sort",)}),
        ("Популярный", {"fields": ("popular_views_threshold",)}),
        ("Сорт недели", {"fields": ("week_special_views_threshold",)}),
        ("Новый", {"fields": ("new_period",)}),
        ("Заканчивается", {"fields": ("ending_stock_threshold",)}),
        ("Хит продаж", {"fields": ("bestseller_sales_threshold", "bestseller_period_days")}),
    )

    def has_add_permission(self, request):
        return not CatalogFilterSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(GrindType)
class GrindTypeAdmin(ModelAdmin):
    list_display = ["name", "slug", "order", "is_active"]
    list_editable = ["order", "is_active"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(RoastType)
class RoastTypeAdmin(ModelAdmin):
    list_display = ["name", "slug", "order", "is_active"]
    list_editable = ["order", "is_active"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Cafe)
class CafeAdmin(ModelAdmin):
    list_display = ["name", "city", "address", "is_active", "order"]
    list_editable = ["is_active", "order"]
    list_filter = ["is_active", "city"]
    search_fields = ["name", "address"]
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ["products"]
    fieldsets = (
        (None, {"fields": ("name", "slug", "is_active", "order")}),
        ("Адрес и контакты", {"fields": ("city", "address", "phone", "working_hours")}),
        ("Координаты", {"fields": ("latitude", "longitude")}),
        ("Контент", {"fields": ("description", "image")}),
        ("Товары", {"fields": ("products",)}),
    )


@admin.register(NavMenuItem)
class NavMenuItemAdmin(ModelAdmin):
    """Пункты дополнительного меню «Купить» (управляются из админки)."""
    list_display = ["title", "url", "order", "is_active", "open_in_new_tab", "show_external_icon"]
    list_editable = ["order", "is_active", "open_in_new_tab", "show_external_icon"]
    search_fields = ["title", "url"]
    fieldsets = (
        (None, {"fields": ("title", "url", "order", "is_active")}),
        ("Отображение", {"fields": ("open_in_new_tab", "show_external_icon")}),
    )


@admin.register(PromoSlide)
class PromoSlideAdmin(ModelAdmin):
    """Промо-слайды «Журнал» на главной странице.

    Слайды отображаются в карусели рядом с блоком «Сорта недели».
    Первый (USP) слайд захардкожен; всё остальное управляется здесь.
    """

    list_display = ["order", "section_label", "title_short", "link_url", "is_active", "preview"]
    list_editable = ["order", "is_active"]
    list_display_links = ["title_short"]
    search_fields = ["title", "section_label"]
    ordering = ["order"]

    fieldsets = (
        (None, {
            "fields": ("section_label", "title", "is_usp", "order", "is_active"),
        }),
        ("Настройки УТП (USP)", {
            "fields": ("usp_line_1_html", "usp_line_2_html", "usp_line_3_html"),
            "description": "Эти поля используются только в том случае, если включен флаг «Является USP/УТП слайдом». Допускается HTML-разметка.",
        }),
        ("Кнопка", {
            "fields": ("link_url", "link_text"),
            "description": "Если URL пустой — кнопка не отображается. Не используется для УТП слайдов.",
        }),
        ("Фоновое изображение", {
            "fields": ("background_image_url", "background_image", "image_opacity"),
            "description": "URL приоритетнее загруженного файла.",
        }),
    )

    @admin.display(description="Заголовок")
    def title_short(self, obj):
        return obj.title[:70] + ("…" if len(obj.title) > 70 else "")

    @admin.display(description="Превью")
    def preview(self, obj):
        url = obj.get_bg_url()
        if url:
            return format_html(
                '<img src="{}" style="height:48px;width:80px;object-fit:cover;border-radius:6px;">',
                url,
            )
        return "—"
