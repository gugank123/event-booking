import re

from rest_framework import serializers

from .models import Booking


class EventRosterBookingSerializer(serializers.ModelSerializer):
    attendeeName = serializers.SerializerMethodField()
    attendeeEmail = serializers.CharField(source="user.email", read_only=True)
    ticketTypeName = serializers.CharField(source="ticket_type.name", read_only=True)
    totalAmount = serializers.DecimalField(source="total_amount", max_digits=10, decimal_places=2, read_only=True)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)

    class Meta:
        model = Booking
        fields = [
            "id", "attendeeName", "attendeeEmail", "ticketTypeName", "quantity",
            "totalAmount", "reference", "status", "createdAt",
        ]

    def get_attendeeName(self, obj):
        return (obj.user.get_full_name() or obj.user.email).strip()


class BookingEventSummarySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    startsAt = serializers.DateTimeField(source="starts_at")
    venue = serializers.CharField()
    city = serializers.CharField()
    imageUrl = serializers.CharField(source="image_url")
    status = serializers.CharField()


class MyBookingSerializer(serializers.ModelSerializer):
    event = BookingEventSummarySerializer(read_only=True)
    ticketTypeName = serializers.CharField(source="ticket_type.name", read_only=True)
    totalAmount = serializers.DecimalField(source="total_amount", max_digits=10, decimal_places=2, read_only=True)
    cardLast4 = serializers.CharField(source="card_last4", read_only=True)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)

    class Meta:
        model = Booking
        fields = [
            "id", "event", "ticketTypeName", "quantity", "totalAmount",
            "reference", "status", "cardLast4", "createdAt",
        ]


class CheckoutSerializer(serializers.Serializer):
    eventId = serializers.IntegerField()
    ticketTypeId = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)
    cardNumber = serializers.CharField(write_only=True)
    expiry = serializers.CharField(write_only=True)
    cvc = serializers.CharField(write_only=True)

    def validate_cardNumber(self, value):
        digits = re.sub(r"\s", "", value)
        if not re.fullmatch(r"\d{12,19}", digits):
            raise serializers.ValidationError("That card number doesn't look right.")
        return digits

    def validate_expiry(self, value):
        if not re.fullmatch(r"(0[1-9]|1[0-2])/\d{2}", value):
            raise serializers.ValidationError("Expiry should be in MM/YY format.")
        return value

    def validate_cvc(self, value):
        if not re.fullmatch(r"\d{3,4}", value):
            raise serializers.ValidationError("CVC should be 3 or 4 digits.")
        return value
