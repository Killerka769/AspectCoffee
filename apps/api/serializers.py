
from rest_framework import serializers
from apps.catalog.models import (
    Category, Product, ProductVariant, ProductImage,
    FlavorNote, BrewMethod, Tag, Recipe, Review,
)
from apps.orders.models import Cart, CartItem, Order, OrderItem, PromoCode
from apps.users.models import User, Address
class CategorySerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()
    class Meta:
        model = Category
        fields = ["id", "name", "slug", "parent", "children", "image", "seo_title", "seo_description", "h1"]
    def get_children(self, obj):
        children = obj.children.filter(is_active=True)
        return CategorySerializer(children, many=True, context=self.context).data
class FlavorNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = FlavorNote
        fields = ["id", "name", "slug"]
class BrewMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = BrewMethod
        fields = ["id", "name", "slug"]
class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name", "slug"]
class ProductVariantSerializer(serializers.ModelSerializer):
    grind = serializers.CharField(read_only=True)
    grind_display = serializers.CharField(source="get_grind_display", read_only=True)
    roast = serializers.SerializerMethodField()
    roast_display = serializers.CharField(read_only=True)
    available = serializers.BooleanField(read_only=True)
    class Meta:
        model = ProductVariant
        fields = ["id", "weight", "grind", "grind_display", "roast", "roast_display", "price", "old_price", "stock_qty", "sku", "is_preorder", "available"]

    def get_roast(self, obj):
        return obj.roast_type.slug if obj.roast_type_id else ""
class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ["id", "image", "alt", "order"]
class ProductListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    min_price = serializers.SerializerMethodField()
    roast_display = serializers.CharField(source="get_roast_level_display", read_only=True)
    class Meta:
        model = Product
        fields = [
            "id", "slug", "name", "main_image", "category_name",
            "roast_level", "roast_display", "origin_country",
            "min_price", "rating_avg", "reviews_count",
            "is_featured", "is_new", "is_bestseller", "in_stock",
        ]
    def get_min_price(self, obj):
        variants = obj.variants.all()
        if variants:
            return min(v.price for v in variants)
        return None
class ProductDetailSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    flavor_notes = FlavorNoteSerializer(many=True, read_only=True)
    brew_methods = BrewMethodSerializer(many=True, read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    roast_display = serializers.CharField(source="get_roast_level_display", read_only=True)
    related_products = ProductListSerializer(many=True, read_only=True)
    class Meta:
        model = Product
        fields = [
            "id", "slug", "name", "description", "short_description",
            "category", "main_image", "images",
            "roast_level", "roast_display", "origin_country", "composition",
            "processing_method", "flavor_description_html",
            "body", "acidity", "sweetness",
            "flavor_notes", "brew_methods", "tags",
            "variants", "related_products",
            "is_active", "is_featured", "in_stock",
            "rating_avg", "reviews_count",
            "seo_title", "seo_description",
            "created_at", "updated_at",
        ]
class ReviewSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    class Meta:
        model = Review
        fields = ["id", "rating", "delivery_rating", "delivery_text", "delivery_operator", "text", "author_name", "created_at"]
        read_only_fields = ["is_approved", "created_at"]
    def get_author_name(self, obj):
        if obj.user:
            return obj.user.get_full_name() or obj.user.email
        return obj.author_name or "Аноним"
    def create(self, validated_data):
        request = self.context["request"]
        validated_data["user"] = request.user if request.user.is_authenticated else None
        # Отзыв уходит на модерацию (status='new' по умолчанию, is_approved=False).
        return super().create(validated_data)
class RecipeSerializer(serializers.ModelSerializer):
    brew_method = BrewMethodSerializer(read_only=True)
    difficulty_display = serializers.CharField(source="get_difficulty_display", read_only=True)
    class Meta:
        model = Recipe
        fields = [
            "id", "slug", "name", "brew_method", "difficulty", "difficulty_display",
            "time_minutes", "description", "ingredients", "main_image", "video_url",
            "is_published", "created_at",
        ]
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True)
    class Meta:
        model = User
        fields = ["email", "first_name", "last_name", "phone", "password", "password2"]
    def validate(self, attrs):
        if attrs["password"] != attrs.pop("password2"):
            raise serializers.ValidationError({"password": "Пароли не совпадают"})
        return attrs
    def validate_phone(self, value):
        from apps.users.phone_confirmation import normalize_phone, phone_owner

        phone = normalize_phone(value)
        if value and not phone:
            raise serializers.ValidationError("Введите корректный номер телефона")
        if phone and phone_owner(phone):
            raise serializers.ValidationError(
                "Этот номер уже используется другой учётной записью"
            )
        return phone
    def create(self, validated_data):
        validated_data["phone_confirmed"] = bool(validated_data.get("phone"))
        return User.objects.create_user(**validated_data)
class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "phone", "avatar", "bonus_points"]
        read_only_fields = ["email", "bonus_points"]
class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ["id", "label", "city", "street", "apartment", "postal_code", "is_default"]
class CartItemSerializer(serializers.ModelSerializer):
    variant = ProductVariantSerializer(read_only=True)
    variant_id = serializers.PrimaryKeyRelatedField(
        queryset=ProductVariant.objects.all(), source="variant", write_only=True,
    )
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    product_name = serializers.CharField(source="variant.product.name", read_only=True)
    product_slug = serializers.CharField(source="variant.product.slug", read_only=True)
    product_image = serializers.ImageField(source="variant.product.main_image", read_only=True)
    class Meta:
        model = CartItem
        fields = ["id", "variant", "variant_id", "qty", "total_price", "product_name", "product_slug", "product_image"]
class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    discount_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    total_items = serializers.IntegerField(read_only=True)
    promo_code_applied = serializers.CharField(source="promo_code.code", read_only=True, allow_null=True)
    class Meta:
        model = Cart
        fields = ["id", "items", "subtotal", "discount_amount", "total", "total_items", "promo_code_applied"]
class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ["id", "product_name", "variant_description", "qty", "price_at_order", "total_price"]
class OrderCreateSerializer(serializers.Serializer):
    delivery_type = serializers.ChoiceField(choices=Order.DELIVERY_CHOICES)
    delivery_address = serializers.JSONField()
    payment_method = serializers.ChoiceField(choices=Order.PAYMENT_CHOICES)
    contact_name = serializers.CharField(max_length=200)
    contact_phone = serializers.CharField(max_length=20)
    contact_email = serializers.EmailField()
    comment = serializers.CharField(max_length=1000, required=False, allow_blank=True)

    def validate_delivery_address(self, value):
        from django.utils.html import escape
        if isinstance(value, dict):
            return {k: escape(str(v)) for k, v in value.items()}
        return escape(str(value))
class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    delivery_type_display = serializers.CharField(source="get_delivery_type_display", read_only=True)
    payment_method_display = serializers.CharField(source="get_payment_method_display", read_only=True)
    class Meta:
        model = Order
        fields = [
            "id", "status", "status_display",
            "delivery_type", "delivery_type_display", "delivery_address",
            "delivery_cost", "cdek_track_number",
            "payment_method", "payment_method_display", "payment_status",
            "discount_amount", "total_amount",
            "contact_name", "contact_phone", "contact_email", "comment",
            "items", "created_at", "updated_at",
        ]
        read_only_fields = ["status", "payment_status", "cdek_track_number", "created_at", "updated_at"]
class PromoApplySerializer(serializers.Serializer):
    code = serializers.CharField(max_length=50)
