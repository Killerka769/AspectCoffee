
from django.urls import path
from apps.payments.views import PaymentWebhookView, CreatePaymentView, InitiateRefundView

urlpatterns = [
    path("payments/webhook/", PaymentWebhookView.as_view(), name="payment-webhook"),
    path("payments/create/", CreatePaymentView.as_view(), name="payment-create"),
    path("payments/refund/<int:order_id>/", InitiateRefundView.as_view(), name="payment-refund"),
]
