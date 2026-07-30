
import django_filters
from .models import Product, Category, FlavorNote, BrewMethod
class ProductFilter(django_filters.FilterSet):
    roast_level = django_filters.MultipleChoiceFilter(
        choices=Product.ROAST_CHOICES,
        label="Степень обжарки",
    )
    brew_methods = django_filters.ModelMultipleChoiceFilter(
        queryset=BrewMethod.objects.all(),
        field_name="brew_methods",
        label="Способ приготовления",
    )
    flavor_notes = django_filters.ModelMultipleChoiceFilter(
        queryset=FlavorNote.objects.all(),
        field_name="flavor_notes",
        label="Вкусовые нотки",
    )
    origin_country = django_filters.CharFilter(
        field_name="origin_country",
        lookup_expr="icontains",
        label="Страна",
    )
    price_min = django_filters.NumberFilter(
        field_name="variants__price",
        lookup_expr="gte",
        label="Цена от",
    )
    price_max = django_filters.NumberFilter(
        field_name="variants__price",
        lookup_expr="lte",
        label="Цена до",
    )
    weight = django_filters.MultipleChoiceFilter(
        field_name="variants__weight",
        choices=[
            (100, "100 г"), (250, "250 г"),
            (500, "500 г"), (1000, "1 кг"),
        ],
        label="Вес",
    )
    in_stock = django_filters.BooleanFilter(label="В наличии")
    category = django_filters.ModelChoiceFilter(
        queryset=Category.objects.filter(is_active=True),
        field_name="category",
        label="Категория",
    )
    search = django_filters.CharFilter(
        field_name="name",
        lookup_expr="icontains",
        label="Поиск",
    )
    ORDERING_CHOICES = [
        ("rating_avg", "По рейтингу ↑"),
        ("-rating_avg", "По рейтингу ↓"),
        ("variants__price", "По цене ↑"),
        ("-variants__price", "По цене ↓"),
        ("-created_at", "Новинки"),
        ("name", "По названию"),
    ]
    ordering = django_filters.OrderingFilter(
        choices=ORDERING_CHOICES,
        fields={
            "rating_avg": "rating_avg",
            "created_at": "created_at",
            "name": "name",
            "variants__price": "variants__price",
        },
    )
    class Meta:
        model = Product
        fields = [
            "roast_level", "brew_methods", "flavor_notes",
            "origin_country", "price_min", "price_max",
            "weight", "in_stock", "category", "search", "ordering",
        ]
