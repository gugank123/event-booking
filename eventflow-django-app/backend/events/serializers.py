from django.db import models
from rest_framework import serializers

from .models import Event, Review, Seat, TicketType, Wishlist


class TicketTypeSerializer(serializers.ModelSerializer):
    remaining = serializers.IntegerField(read_only=True)

    class Meta:
        model = TicketType
        fields = [
            "id", "name", "price", "quantity_total", "quantity_sold", "remaining",
            "max_per_user", "sale_start", "sale_end",
        ]
        read_only_fields = ["id", "quantity_sold", "remaining"]

    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Price can't be negative.")
        return value

    def validate_quantity_total(self, value):
        if value < 1:
            raise serializers.ValidationError("Quantity must be at least 1.")
        return value

    def validate(self, attrs):
        max_per_user = attrs.get("max_per_user")
        total = attrs.get("quantity_total")
        if max_per_user is not None and max_per_user < 1:
            raise serializers.ValidationError({"max_per_user": "Must allow at least 1 ticket per user."})
        if max_per_user and total and max_per_user > total:
            raise serializers.ValidationError(
                {"max_per_user": "Maximum per user can't exceed total tickets."}
            )
        sale_start = attrs.get("sale_start")
        sale_end = attrs.get("sale_end")
        if sale_start and sale_end and sale_end <= sale_start:
            raise serializers.ValidationError({"sale_end": "Sale end must be after sale start."})
        return attrs


class SeatSerializer(serializers.ModelSerializer):
    label = serializers.SerializerMethodField()

    class Meta:
        model = Seat
        fields = ["id", "section", "row_label", "number", "price", "status", "label"]
        read_only_fields = ["id", "status", "label"]

    def get_label(self, obj):
        return f"{obj.section} {obj.row_label}{obj.number}"


class EventReadSerializer(serializers.ModelSerializer):
    """Full, nested representation used for every response body."""

    ticket_types = TicketTypeSerializer(many=True, read_only=True)
    seats = serializers.SerializerMethodField()
    organizer_name = serializers.SerializerMethodField()
    display_image = serializers.SerializerMethodField()
    avg_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    tickets_sold = serializers.SerializerMethodField()
    bookings_count = serializers.SerializerMethodField()
    is_wishlisted = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = [
            "id", "organizer", "organizer_name", "organizer_contact",
            "title", "short_description", "description", "category",
            "venue", "address", "city", "state", "pincode", "map_link",
            "starts_at", "ends_at", "booking_opens_at", "booking_closes_at",
            "seating_type", "image_url", "display_image",
            "status", "is_featured", "created_at", "ticket_types", "seats",
            "avg_rating", "review_count", "tickets_sold", "bookings_count", "is_wishlisted",
        ]

    def get_organizer_name(self, obj):
        return (obj.organizer.get_full_name() or obj.organizer.email).strip()

    def get_display_image(self, obj):
        try:
            return obj.display_image or ""
        except Exception:
            return obj.image_url or ""

    def get_seats(self, obj):
        # Only expose the seat map when reserved seating is configured; the
        # list can be long, so cap it and let the booking flow handle the rest.
        if obj.seating_type != Event.SeatingType.RESERVED:
            return []
        seats = getattr(obj, "_prefetched_seats", None)
        if seats is None:
            seats = obj.seats.all()[:2000]
        return SeatSerializer(seats, many=True).data

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

    def get_bookings_count(self, obj):
        count = getattr(obj, "bookings_count", None)
        if count is None:
            count = obj.bookings.count()
        return count

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
            "title", "short_description", "description", "category", "organizer_contact",
            "venue", "address", "city", "state", "pincode", "map_link",
            "starts_at", "ends_at", "booking_opens_at", "booking_closes_at",
            "seating_type", "image_url", "status", "is_featured", "ticket_types",
        ]

    def validate_title(self, value):
        if not (value or "").strip():
            raise serializers.ValidationError("Title cannot be empty.")
        return value.strip()

    def validate_description(self, value):
        if not (value or "").strip():
            raise serializers.ValidationError("Description cannot be empty.")
        return value.strip()

    def validate(self, attrs):
        starts_at = attrs.get("starts_at")
        ends_at = attrs.get("ends_at")
        if starts_at and ends_at and ends_at <= starts_at:
            raise serializers.ValidationError({"ends_at": "End time must be after start time."})
        opens_at = attrs.get("booking_opens_at")
        closes_at = attrs.get("booking_closes_at")
        if opens_at and closes_at and closes_at <= opens_at:
            raise serializers.ValidationError(
                {"booking_closes_at": "Booking closing must be after booking opening."}
            )
        if closes_at and starts_at and closes_at > starts_at:
            raise serializers.ValidationError(
                {"booking_closes_at": "Booking cannot close after the event starts."}
            )
        if not attrs.get("venue", "").strip() or not attrs.get("city", "").strip():
            raise serializers.ValidationError("Venue and city are required.")
        return attrs

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
            "title", "short_description", "description", "category", "organizer_contact",
            "venue", "address", "city", "state", "pincode", "map_link",
            "starts_at", "ends_at", "booking_opens_at", "booking_closes_at",
            "seating_type", "image_url", "status", "is_featured",
        ]
        extra_kwargs = {field: {"required": False} for field in fields}

    def validate(self, attrs):
        starts_at = attrs.get("starts_at", getattr(self.instance, "starts_at", None))
        ends_at = attrs.get("ends_at", getattr(self.instance, "ends_at", None))
        if starts_at and ends_at and ends_at <= starts_at:
            raise serializers.ValidationError({"ends_at": "End time must be after start time."})
        closes_at = attrs.get("booking_closes_at", getattr(self.instance, "booking_closes_at", None))
        if closes_at and starts_at and closes_at > starts_at:
            raise serializers.ValidationError(
                {"booking_closes_at": "Booking cannot close after the event starts."}
            )
        new_status = attrs.get("status")
        if new_status and self.instance and new_status != self.instance.status:
            allowed = Event.VALID_TRANSITIONS.get(self.instance.status, set())
            if new_status not in allowed:
                raise serializers.ValidationError(
                    {"status": f"Cannot move event from {self.instance.status} to {new_status}."}
                )
        return attrs


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
