from django.urls import path
from .yookassa_views import YookassaPaymentView, yookassa_webhook
from . import views

app_name = "users"

urlpatterns = [
    path("profile/", views.profile, name="profile"),
    path("complete-phone/", views.complete_phone, name="complete_phone"),
    path("profile/change-password/", views.change_password, name="change_password"),
    path("profile/delete/", views.delete_account, name="delete_account"),
    path("verify-email/", views.verify_email, name="verify_email"),
    path("resend-verification/", views.resend_verification, name="resend_verification"),
    path("orders/", views.orders_history, name="orders"),
    path("orders/<int:pk>/", views.order_detail, name="order_detail"),
    path("orders/<int:pk>/cancel/", views.cancel_order, name="cancel_order"),
    path("orders/<int:pk>/reorder/", views.reorder, name="reorder"),
    path("orders/<int:pk>/recurring/cancel/", views.cancel_recurring_order, name="cancel_recurring_order"),
    path("orders/<int:pk>/invoice/", views.download_invoice, name="download_invoice"),
    path("addresses/", views.addresses_view, name="addresses"),
    path("wishlist/", views.wishlist_view, name="wishlist"),
    path("wishlist/add/<int:product_id>/", views.add_to_wishlist, name="add_to_wishlist"),
    path("wishlist/remove/<int:product_id>/", views.remove_from_wishlist, name="remove_from_wishlist"),
    path("discount/", views.discount_view, name="discount"),
    path("balance/", views.balance_view, name="balance"),
    path("balance/topup/", views.topup_balance, name="topup_balance"),
    path("balance/webhook/", yookassa_webhook, name="balance_webhook"),
    path("promo/", views.promo_view, name="promo"),
    path("navigation/", views.navigation_view, name="navigation"),
    path("statistics/", views.statistics_view, name="statistics"),
    path("notifications/", views.notifications_view, name="notifications"),
    path("notifications/push/config/", views.push_config, name="push_config"),
    path("notifications/push/subscribe/", views.push_subscribe, name="push_subscribe"),
    path("notifications/push/unsubscribe/", views.push_unsubscribe, name="push_unsubscribe"),
    path("community-profile/", views.community_profile_view, name="community_profile"),
    path("blacklist/", views.blacklist_view, name="blacklist"),
    path("blacklist/unblock/<int:pk>/", views.unblock_user, name="unblock_user"),
    path("notice/dismiss/<str:key>/", views.dismiss_notice, name="dismiss_notice"),
    path("wishlist/count/", views.wishlist_count, name="wishlist_count"),
    path("notes/save/<int:product_id>/", views.save_note, name="save_note"),
    path("notes/delete/<int:product_id>/", views.delete_note, name="delete_note"),
    path("api/payment/yookassa/init/", YookassaPaymentView.as_view(), name="yookassa_init"),
]

urlpatterns += [
    path("register/", views.register, name="register"),
    path("wishlist/toggle/", views.wishlist_toggle, name="wishlist_toggle"),
    path("wishlist/mini/", views.mini_wishlist, name="mini_wishlist"),
    path("notifications/mini/", views.mini_notifications, name="mini_notifications"),
    path("sync-local/", views.sync_local_storage, name="sync_local"),
]