from django.db import models
from rest_framework import serializers

from .models import Event, Review, TicketType, Wishlist


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
    avg_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    tickets_sold = serializers.SerializerMethodField()
    is_wishlisted = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = [
            "id", "organizer", "organizer_name", "title", "description", "category",
            "venue", "city", "starts_at", "ends_at", "image_url", "status",
            "is_featured", "created_at", "ticket_types",
            "avg_rating", "review_count", "tickets_sold", "is_wishlisted",
        ]

    def get_organizer_name(self, obj):
        return (obj.organizer.get_full_name() or obj.organizer.email).strip()

    def get_avg_rating(self, obj):
        avg = getattr(obj, "avg_rating", None)
        if avg is None:
            agg = obj.reviews.aggregate(avg=models.Avg("rating"))
            avg = agg["avg"]
        return round(float(avg), 1) if avg is not None else None

    def get_review_count(self, obj):
        count = getattr(obj, "review_count", None)
        if count is None:
            count = obj.reviews.count()
        return count

    def get_tickets_sold(self, obj):
        sold = getattr(obj, "tickets_sold", None)
        if sold is None:
            agg = obj.ticket_types.aggregate(sold=models.Sum("quantity_sold"))
            sold = agg["sold"] or 0
        return sold

    def get_is_wishlisted(self, obj):
        wishlist_ids = (self.context or {}).get("wishlist_ids")
        if wishlist_ids is None:
            return False
        return obj.pk in wishlist_ids


class EventCreateSerializer(serializers.ModelSerializer):
    """Used only for POST -- requires at least one ticket type up front."""

    ticket_types = TicketTypeSerializer(many=True)

    class Meta:
        model = Event
        fields = [
            "title", "description", "category", "venue", "city",
            "starts_at", "ends_at", "image_url", "status", "is_featured", "ticket_types",
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
            "starts_at", "ends_at", "image_url", "status", "is_featured",
        ]
        extra_kwargs = {field: {"required": False} for field in fields}


class ReviewSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    mine = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = ["id", "event", "author_name", "rating", "comment", "created_at", "updated_at", "mine"]
        read_only_fields = ["id", "event", "author_name", "created_at", "updated_at", "mine"]

    def get_author_name(self, obj):
        return (obj.user.get_full_name() or obj.user.email).strip()

    def get_mine(self, obj):
        request = (self.context or {}).get("request")
        return bool(request and request.user.is_authenticated and obj.user_id == request.user.id)

    def validate_rating(self, value):
        if not 1 <= value <= 5:
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value


class WishlistSerializer(serializers.ModelSerializer):
    event = EventReadSerializer(read_only=True)

    class Meta:
        model = Wishlist
        fields = ["event", "created_at"]
