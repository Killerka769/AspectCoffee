
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import (
    RegisterView, LogoutView, EmailConfirmView,
    DeliveryCalcView, DeliveryPVZView,
    CategoryViewSet, ProductViewSet,
    CartView, CartItemView, CartPromoView,
    OrderViewSet, SearchSuggestView,
)
router = DefaultRouter()
router.register(r"catalog/categories", CategoryViewSet, basename="category")
router.register(r"catalog/products", ProductViewSet, basename="product")
# router.register(r"catalog/recipes", RecipeViewSet, basename="recipe")
router.register(r"orders", OrderViewSet, basename="order")
urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/confirm-email/", EmailConfirmView.as_view(), name="confirm-email"),
    path("auth/login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("cart/", CartView.as_view(), name="cart"),
    path("cart/items/", CartItemView.as_view(), name="cart-items"),
    path("cart/items/<int:pk>/", CartItemView.as_view(), name="cart-item-detail"),
    path("cart/promo/", CartPromoView.as_view(), name="cart-promo"),
    path("delivery/calc/", DeliveryCalcView.as_view(), name="delivery-calc"),
    path("delivery/pvz/", DeliveryPVZView.as_view(), name="delivery-pvz"),
    path("search/suggest/", SearchSuggestView.as_view(), name="search-suggest"),
    path("", include(router.urls)),
]
