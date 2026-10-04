from rest_framework import serializers

from .models import Booking


class EventRosterBookingSerializer(serializers.ModelSerializer):
    attendeeName = serializers.SerializerMethodField()
    attendeeEmail = serializers.CharField(source="user.email", read_only=True)
    ticketTypeName = serializers.CharField(source="ticket_type.name", read_only=True)
    totalAmount = serializers.DecimalField(source="total_amount", max_digits=10, decimal_places=2, read_only=True)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    checkedIn = serializers.BooleanField(source="checked_in", read_only=True)
    checkedInAt = serializers.DateTimeField(source="checked_in_at", read_only=True)

    class Meta:
        model = Booking
        fields = [
            "id", "attendeeName", "attendeeEmail", "ticketTypeName", "quantity",
            "totalAmount", "reference", "status", "createdAt",
            "checkedIn", "checkedInAt",
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
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    discount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    platformFee = serializers.DecimalField(source="platform_fee", max_digits=10, decimal_places=2, read_only=True)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    checkedIn = serializers.BooleanField(source="checked_in", read_only=True)
    checkedInAt = serializers.DateTimeField(source="checked_in_at", read_only=True)
    expiresAt = serializers.DateTimeField(source="expires_at", read_only=True)
    seats = serializers.SerializerMethodField()
    tickets = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
            "id", "event", "ticketTypeName", "quantity", "subtotal", "discount",
            "platformFee", "totalAmount", "coupon_code", "reference", "status",
            "createdAt", "expiresAt", "checkedIn", "checkedInAt", "seats", "tickets",
        ]

    def get_seats(self, obj):
        return [f"{s.section} {s.row_label}{s.number}" for s in obj.seats.all()]

    def get_tickets(self, obj):
        from payments.serializers import TicketSerializer

        return TicketSerializer(obj.tickets.all(), many=True).data


class BookingCreateSerializer(serializers.Serializer):
    """Real checkout input: NO card fields. Prices computed server-side."""

    eventId = serializers.IntegerField()
    ticketTypeId = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1, max_value=10, required=False, default=1)
    seat_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1), required=False, default=list
    )
    coupon_code = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, attrs):
        if len(attrs.get("seat_ids", [])) > 10:
            raise serializers.ValidationError({"seat_ids": "You can select at most 10 seats per booking."})
        return attrs
