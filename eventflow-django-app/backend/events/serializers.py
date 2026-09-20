from rest_framework import serializers

from .models import Event, TicketType


class TicketTypeSerializer(serializers.ModelSerializer):
    remaining = serializers.IntegerField(read_only=True)

    class Meta:
        model = TicketType
        fields = ["id", "name", "price", "quantity_total", "quantity_sold", "remaining"]
        read_only_fields = ["id", "quantity_sold", "remaining"]

    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Price can't be negative.")
        return value

    def validate_quantity_total(self, value):
        if value < 1:
            raise serializers.ValidationError("Quantity must be at least 1.")
        return value


class EventReadSerializer(serializers.ModelSerializer):
    """Full, nested representation used for every response body."""

    ticket_types = TicketTypeSerializer(many=True, read_only=True)
    organizer_name = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = [
            "id", "organizer", "organizer_name", "title", "description", "category",
            "venue", "city", "starts_at", "ends_at", "image_url", "status",
            "created_at", "ticket_types",
        ]

    def get_organizer_name(self, obj):
        return (obj.organizer.get_full_name() or obj.organizer.email).strip()


class EventCreateSerializer(serializers.ModelSerializer):
    """Used only for POST -- requires at least one ticket type up front."""

    ticket_types = TicketTypeSerializer(many=True)

    class Meta:
        model = Event
        fields = [
            "title", "description", "category", "venue", "city",
            "starts_at", "ends_at", "image_url", "status", "ticket_types",
        ]

    def validate_ticket_types(self, value):
        if not value:
            raise serializers.ValidationError("Add at least one ticket type.")
        return value

    def create(self, validated_data):
        ticket_types_data = validated_data.pop("ticket_types")
        event = Event.objects.create(organizer=self.context["request"].user, **validated_data)
        for tt in ticket_types_data:
            TicketType.objects.create(event=event, **tt)
        return event


class EventUpdateSerializer(serializers.ModelSerializer):
    """Used for PATCH/PUT -- plain field edits, ticket types managed separately."""

    class Meta:
        model = Event
        fields = [
            "title", "description", "category", "venue", "city",
            "starts_at", "ends_at", "image_url", "status",
        ]
        extra_kwargs = {field: {"required": False} for field in fields}
