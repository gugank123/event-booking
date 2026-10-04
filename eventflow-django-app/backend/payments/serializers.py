from rest_framework import serializers

from .models import Coupon, Payment, Refund, Ticket


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ["id", "booking", "gateway", "gateway_order_id", "gateway_payment_id",
                  "amount", "currency", "status", "created_at", "updated_at"]
        read_only_fields = fields


class RefundSerializer(serializers.ModelSerializer):
    class Meta:
        model = Refund
        fields = ["id", "payment", "booking", "gateway_refund_id", "amount",
                  "status", "reason", "created_at", "updated_at"]
        read_only_fields = fields


class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = ["id", "code", "discount_type", "discount_value", "max_discount",
                  "min_booking_amount", "starts_at", "expires_at", "usage_limit",
                  "per_user_limit", "times_used", "is_active"]
        read_only_fields = ["id", "times_used"]


class TicketSerializer(serializers.ModelSerializer):
    eventTitle = serializers.CharField(source="event.title", read_only=True)
    seatLabel = serializers.SerializerMethodField()
    bookingReference = serializers.CharField(source="booking.reference", read_only=True)

    class Meta:
        model = Ticket
        fields = ["id", "ticket_number", "qr_token", "booking", "bookingReference",
                  "event", "eventTitle", "seat", "seatLabel", "status", "used_at", "created_at"]
        read_only_fields = fields

    def get_seatLabel(self, obj):
        if obj.seat:
            return f"{obj.seat.section} {obj.seat.row_label}{obj.seat.number}"
        return ""
