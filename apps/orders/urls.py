from django.urls import path
from . import views

app_name = "orders"

urlpatterns = [
    path("basket/", views.basket_view, name="basket"),
    path("basket/account-status/", views.checkout_account_status, name="checkout_account_status"),
    path("basket/add/", views.add_to_cart, name="add_to_cart"),
    path("basket/update/<int:variant_id>/", views.update_cart, name="update_cart"),
    path("basket/remove/<int:variant_id>/", views.remove_from_cart, name="remove_from_cart"),
    path("basket/promo/", views.apply_promo, name="apply_promo"),
    path("basket/badge/", views.cart_badge, name="cart_badge"),
    path("basket/data.json", views.cart_data_json, name="cart_data_json"),
    path("basket/mini/", views.mini_cart, name="mini_cart"),
    path("basket/address/<int:address_id>/edit/", views.edit_address, name="edit_address"),
    path("basket/address/<int:address_id>/delete/", views.delete_address, name="delete_address"),
    path("order/success/<int:order_id>/", views.order_success, name="order_success"),
    path("order/<int:order_id>/resume-payment/", views.resume_order_payment, name="resume_payment"),
    path("compare/badge/", views.compare_badge, name="compare_badge"),
    path("wishlist/badge/", views.wishlist_badge, name="wishlist_badge"),
]
