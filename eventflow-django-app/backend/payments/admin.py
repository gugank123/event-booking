from django.contrib import admin

from .models import Coupon, CouponRedemption, Payment, Refund, Ticket


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("gateway_order_id", "booking", "amount", "currency", "status", "created_at")
    list_filter = ("status", "gateway")
    search_fields = ("gateway_order_id", "gateway_payment_id", "booking__reference")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = ("id", "booking", "amount", "status", "gateway_refund_id", "created_at")
    list_filter = ("status",)
    search_fields = ("gateway_refund_id", "booking__reference")


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ("code", "discount_type", "discount_value", "is_active", "times_used", "expires_at")
    list_filter = ("discount_type", "is_active")
    search_fields = ("code",)


@admin.register(CouponRedemption)
class CouponRedemptionAdmin(admin.ModelAdmin):
    list_display = ("coupon", "user", "booking", "discount_amount", "created_at")
    search_fields = ("coupon__code", "user__email")


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("ticket_number", "event", "user", "status", "used_at")
    list_filter = ("status",)
    search_fields = ("ticket_number", "qr_token", "booking__reference", "user__email")
