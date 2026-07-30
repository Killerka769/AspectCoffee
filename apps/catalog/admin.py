
import json
from django import forms
from django.contrib import admin
from django.urls import path, reverse
from django.template.response import TemplateResponse
from django.utils.html import format_html
from django.db.models import Count
from unfold.admin import ModelAdmin, TabularInline, StackedInline
from unfold.decorators import action
from import_export.admin import ImportExportModelAdmin
from .models import (
    Category, Tag, FlavorNote, BrewMethod,
    Product, ProductVariant, ProductImage,
    Recipe, RecipeStep, Review, ParserLog, ParserSetting,
    SiteSettings, CatalogFilterSettings, ProductView,
    GrindType, RoastType, ProductPackaging, Roaster, Cafe,
    NavMenuItem, PromoSlide,
)
from .tasks import run_catalog_parser_task
from apps.pages.models import ReviewComment
from django.contrib import messages
from django.shortcuts import redirect

@admin.register(Roaster)
class RoasterAdmin(ModelAdmin):
    list_display = ["name", "is_active"]
    list_editable = ["is_active"]
    search_fields = ["name"]

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
class ProductPackagingInline(TabularInline):
    model = ProductPackaging
    extra = 1
    fields = ["weight", "price", "old_price", "order", "is_active"]
    ordering = ["order", "weight"]


class ProductVariantInline(TabularInline):
    model = ProductVariant
    extra = 1
    # 1.7.4 — вариант = фасовка × помол × обжарка (цена берётся с фасовки).
    fields = ["packaging", "grind_type", "roast_type", "stock_qty", "sku", "is_preorder"]
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
    list_display = ["name", "category", "roast_level", "in_stock", "is_active", "is_featured", "rating_avg"]
    list_editable = ["is_active", "is_featured", "in_stock"]
    list_filter = ["category", "roast_level", "in_stock", "is_active", "is_featured", "is_new", "is_bestseller", "is_microlot"]
    search_fields = ["name", "slug", "description", "origin_country"]
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ["tags", "flavor_notes", "brew_methods", "related_products"]
    inlines = [ProductPackagingInline, ProductVariantInline, ProductImageInline]
    readonly_fields = ["rating_avg", "reviews_count", "created_at", "updated_at"]
    fieldsets = (
        ("Основное", {"fields": ("name", "slug", "category", "description", "short_description", "main_image")}),
        ("Контентные табы на фронте", {"fields": ("storage_description", "delivery_description")}),
        (
            "Атрибуты кофе",
            {"fields": (
                "roast_level", "processing_method", "origin_country", "region",
                "altitude", "roaster_machine", "roaster",
                "q_score", "harvest_year", "variety", "caffeine_content",
                "composition", "brew_methods", "flavor_notes",
            )},
        ),
        ("Профиль вкуса", {"fields": ("body", "acidity", "sweetness", "flavor_description_html")}),
        ("Флаги", {"fields": ("is_active", "is_featured", "is_new", "is_bestseller", "is_microlot", "in_stock", "tags")}),
        ("Похожие товары", {"fields": ("related_products",)}),
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
class RecipeStepInline(StackedInline):
    model = RecipeStep
    extra = 1
    fields = ["step_number", "description", "image"]


class RecipeAdminForm(forms.ModelForm):
    ingredients = forms.CharField(
        label="Ингредиенты",
        required=False,
        widget=forms.Textarea,
        help_text='Введите JSON-массив: ["вода", "кофе"] или каждый ингредиент с новой строки.',
    )

    class Meta:
        model = Recipe
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and not self.is_bound:
            self.initial["ingredients"] = json.dumps(
                self.instance.ingredients or [],
                ensure_ascii=False,
                indent=2,
            )

    def clean_ingredients(self):
        raw = (self.cleaned_data.get("ingredients") or "").strip()
        if not raw:
            return []
        if raw.startswith("["):
            try:
                value = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise forms.ValidationError(
                    'Неверный JSON. Используйте формат ["вода", "кофе"] или строки по одной.'
                ) from exc
            if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
                raise forms.ValidationError("Ингредиенты должны быть списком строк.")
            return [item.strip() for item in value if item.strip()]

        if raw.startswith("{"):
            raise forms.ValidationError("Ингредиенты должны быть списком, не объектом.")

        items = [line.strip(" \t\r\n-•,") for line in raw.splitlines()]
        items = [item for item in items if item]
        if not items:
            raise forms.ValidationError("Добавьте хотя бы один ингредиент.")
        return items


@admin.register(Recipe)
class RecipeAdmin(ModelAdmin):
    form = RecipeAdminForm
    actions = ["publish", "unpublish"]
    list_display = ["name", "brew_method", "difficulty", "time_minutes", "is_published"]
    list_editable = ["is_published"]
    list_filter = ["brew_method", "difficulty", "is_published"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ["products"]
    readonly_fields = ["author", "is_user_submitted", "created_at", "updated_at"]
    inlines = [RecipeStepInline]
    fieldsets = (
        (None, {"fields": ("name", "slug", "brew_method", "difficulty", "time_minutes", "is_published")}),
        ("Контент", {"fields": ("description", "main_image", "video_url", "ingredients")}),
        ("Связанные товары", {"fields": ("products",)}),
        ("Модерация", {"fields": ("author", "is_user_submitted", "created_at", "updated_at")}),
    )

    def save_model(self, request, obj, form, change):
        was_published = False
        if change and obj.pk:
            was_published = Recipe.objects.filter(pk=obj.pk).values_list(
                "is_published", flat=True
            ).first()
        super().save_model(request, obj, form, change)
        if not was_published and obj.is_published and obj.author_id:
            from apps.catalog.tasks import send_user_recipe_published_notification

            send_user_recipe_published_notification.delay(obj.pk)

    @action(description="Опубликовать")
    def publish(self, request, queryset):
        from apps.catalog.tasks import send_user_recipe_published_notification

        published = 0
        for recipe in queryset.filter(is_published=False):
            recipe.is_published = True
            recipe.save(update_fields=["is_published", "updated_at"])
            if recipe.author_id:
                send_user_recipe_published_notification.delay(recipe.pk)
            published += 1
        self.message_user(request, f"Опубликовано рецептов: {published}")
    @action(description="Снять с публикации")
    def unpublish(self, request, queryset):
        queryset.update(is_published=False)
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
@admin.register(Tag)
class TagAdmin(ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
@admin.register(FlavorNote)
class FlavorNoteAdmin(ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
@admin.register(BrewMethod)
class BrewMethodAdmin(ModelAdmin):
    list_display = ["name", "slug", "guide_url"]
    prepopulated_fields = {"slug": ("name",)}

@admin.register(ParserLog)
class ParserLogAdmin(ModelAdmin):
    list_display = ["started_at", "finished_at", "status", "created_count", "updated_count"]
    readonly_fields = ["started_at", "finished_at", "status", "total_products", "created_count", "updated_count", "errors"]
    actions = ["run_parser_directly"]

    @action(description="Запустить парсинг сейчас")
    def run_parser_directly(self, request, queryset):
        run_catalog_parser_task.delay(force=True)
        messages.success(request, "Задача парсинга запущена в фоновом режиме.")
        return redirect(request.path)

@admin.register(ParserSetting)
class ParserSettingAdmin(ModelAdmin):
    list_display = ["__str__", "is_auto_update_enabled", "last_run_at", "update_interval_hours"]
    list_editable = ["is_auto_update_enabled", "update_interval_hours"]
    actions = ["run_parser_directly"]

    @action(description="Запустить парсинг сейчас")
    def run_parser_directly(self, request, queryset):
        run_catalog_parser_task.delay(force=True)
        messages.success(request, "Задача парсинга запущена в фоновом режиме.")
        return redirect(request.path)

    def has_add_permission(self, request):
        return not ParserSetting.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom = [
            path("run-parser/", self.admin_site.admin_view(self.run_parser_view), name="catalog_parsersetting_run_parser"),
            path("run-parser-result/", self.admin_site.admin_view(self.run_parser_result_view), name="catalog_parsersetting_run_parser_result"),
        ]
        return custom + urls

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["parser_url"] = reverse("admin:catalog_parsersetting_run_parser")
        extra_context["parser_result"] = ParserLog.objects.order_by("-started_at").first()
        return super().changelist_view(request, extra_context=extra_context)

    def render_change_form(self, request, context, *args, **kwargs):
        context = context or {}
        obj = context.get("original")
        extra = {
            "parser_url": reverse("admin:catalog_parsersetting_run_parser"),
            "parser_result": ParserLog.objects.order_by("-started_at").first(),
        }
        context.update(extra)
        return super().render_change_form(request, context, *args, **kwargs)

    def run_parser_view(self, request):
        context = {
            "title": "Запуск парсера каталога",
            "opts": self.model._meta,
            "parser_result": ParserLog.objects.order_by("-started_at").first(),
        }
        if request.method == "POST":
            category = request.POST.get("category", "coffee")
            update_images = request.POST.get("update_images") == "on"
            limit = request.POST.get("limit", 0)
            try:
                limit = int(limit)
            except (ValueError, TypeError):
                limit = 0
            run_catalog_parser_task.delay(force=True, update_images=update_images, category=category, limit=limit)
            messages.success(request, f"Парсер запущен (категория: {category}, обновлять изображения: {'да' if update_images else 'нет'}). Результат появится в логах через некоторое время.")
            return redirect("admin:catalog_parsersetting_run_parser_result")
        return TemplateResponse(request, "admin/catalog/parsersetting/run_parser.html", context)

    def run_parser_result_view(self, request):
        from .models import ParserLog
        context = {
            "title": "Результаты парсера",
            "opts": self.model._meta,
            "logs": ParserLog.objects.order_by("-started_at")[:20],
        }
        return TemplateResponse(request, "admin/catalog/parsersetting/parser_result.html", context)


@admin.register(SiteSettings)
class SiteSettingsAdmin(ModelAdmin):
    fieldsets = (
        ("Основное", {"fields": ("site_name",)}),
        ("Ссылки и контакты", {"fields": ("wholesale_url", "main_site_url", "contact_phone", "contact_telegram", "contact_whatsapp", "free_delivery_min")}),
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
        ("Баннер обжарки", {"fields": ("roast_banner_is_active", "roast_banner_title", "roast_banner_subtitle")}),
        ("Блок «Открытость» (Трансляции)", {
            "fields": (
                "openness_title", "openness_description",
                "openness_stream_1_title", "openness_stream_1_url", "openness_stream_1_image",
                "openness_stream_2_title", "openness_stream_2_url", "openness_stream_2_image",
                "openness_stream_3_title", "openness_stream_3_url", "openness_stream_3_image",
            )
        }),
        ("Рецепты", {"fields": ("allow_recipe_without_order",)}),
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


@admin.register(ProductView)
class ProductViewAdmin(ModelAdmin):
    list_display = ["product", "session_key", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["product__name"]
    readonly_fields = ["product", "session_key", "created_at"]

    def has_add_permission(self, request):
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


@admin.register(ProductPackaging)
class ProductPackagingAdmin(ModelAdmin):
    list_display = ["product", "weight", "price", "old_price", "order", "is_active"]
    list_editable = ["price", "old_price", "order", "is_active"]
    list_filter = ["is_active", "weight"]
    search_fields = ["product__name"]


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
