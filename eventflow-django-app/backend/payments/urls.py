from django.urls import path

from .views import (
    CouponDetailView,
    CouponListView,
    CouponValidateView,
    MyTicketsView,
    PaymentDetailView,
    PaymentOrderView,
    PaymentVerifyView,
    RazorpayWebhookView,
    RefundRequestView,
    RefundStatusView,
    TicketDetailView,
    TicketVerifyView,
)

urlpatterns = [
    path("create-order/", PaymentOrderView.as_view(), name="payment-create-order"),
    path("verify/", PaymentVerifyView.as_view(), name="payment-verify"),
    path("webhook/", RazorpayWebhookView.as_view(), name="payment-webhook"),
    path("<int:pk>/", PaymentDetailView.as_view(), name="payment-detail"),
    path("coupons/validate/", CouponValidateView.as_view(), name="coupon-validate"),
    path("coupons/", CouponListView.as_view(), name="coupon-list"),
    path("coupons/<int:pk>/", CouponDetailView.as_view(), name="coupon-detail"),
    path("tickets/", MyTicketsView.as_view(), name="my-tickets"),
    path("tickets/<int:pk>/", TicketDetailView.as_view(), name="ticket-detail"),
    path("tickets/<int:pk>/verify/", TicketVerifyView.as_view(), name="ticket-verify-pk"),
    path("tickets/verify/", TicketVerifyView.as_view(), name="ticket-verify"),
    path("refunds/<int:booking_id>/request/", RefundRequestView.as_view(), name="refund-request"),
    path("refunds/status/<int:pk>/", RefundStatusView.as_view(), name="refund-status"),
]
