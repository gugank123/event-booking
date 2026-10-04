from django.conf import settings
from django.db import models
from django.utils import timezone


class EventCategory(models.Model):
    """Normalized category list organizers pick from (Event.category kept for compat)."""

    name = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(max_length=60, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Venue(models.Model):
    """Reusable venue record organizers can attach to events."""

    name = models.CharField(max_length=200)
    address = models.CharField(max_length=300, blank=True, default="")
    city = models.CharField(max_length=120, blank=True, default="")
    state = models.CharField(max_length=120, blank=True, default="")
    pincode = models.CharField(max_length=20, blank=True, default="")
    map_link = models.URLField(blank=True, default="")
    capacity = models.PositiveIntegerField(default=0)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="venues"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.city})"


class Event(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        SOLD_OUT = "sold_out", "Sold out"
        CANCELLED = "cancelled", "Cancelled"
        POSTPONED = "postponed", "Postponed"
        COMPLETED = "completed", "Completed"

    # Allowed organizer/admin state transitions (terminal states can't be left).
    VALID_TRANSITIONS = {
        "draft": {"published", "cancelled"},
        "published": {"sold_out", "cancelled", "postponed", "completed", "draft"},
        "sold_out": {"published", "cancelled", "completed"},
        "postponed": {"published", "cancelled"},
        "cancelled": set(),
        "completed": set(),
    }

    class SeatingType(models.TextChoices):
        GENERAL = "general", "General admission"
        RESERVED = "reserved", "Reserved seating"

    organizer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="events")
    title = models.CharField(max_length=200)
    short_description = models.CharField(max_length=300, blank=True, default="")
    description = models.TextField(blank=True, default="")
    category = models.CharField(max_length=60)
    organizer_contact = models.CharField(max_length=200, blank=True, default="")
    venue = models.CharField(max_length=200)
    address = models.CharField(max_length=300, blank=True, default="")
    city = models.CharField(max_length=120)
    state = models.CharField(max_length=120, blank=True, default="")
    pincode = models.CharField(max_length=20, blank=True, default="")
    map_link = models.URLField(blank=True, default="")
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    booking_opens_at = models.DateTimeField(null=True, blank=True)
    booking_closes_at = models.DateTimeField(null=True, blank=True)
    seating_type = models.CharField(max_length=20, choices=SeatingType.choices, default=SeatingType.GENERAL)
    image = models.ImageField(upload_to="event_posters/", null=True, blank=True)
    image_url = models.URLField(blank=True, default="")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PUBLISHED)
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["starts_at"]
        indexes = [
            models.Index(fields=["status", "starts_at"]),
        ]

    def __str__(self):
        return self.title

    @property
    def display_image(self):
        if self.image:
            return self.image.url
        return self.image_url


class TicketType(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="ticket_types")
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity_total = models.PositiveIntegerField()
    quantity_sold = models.PositiveIntegerField(default=0)
    max_per_user = models.PositiveIntegerField(default=8)
    sale_start = models.DateTimeField(null=True, blank=True)
    sale_end = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.event.title})"

    @property
    def remaining(self):
        return self.quantity_total - self.quantity_sold


class Seat(models.Model):
    """A reservable seat for events using reserved seating."""

    class Status(models.TextChoices):
        AVAILABLE = "available", "Available"
        HELD = "held", "Held (temporarily reserved)"
        BOOKED = "booked", "Booked"

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="seats")
    section = models.CharField(max_length=100, default="General")
    row_label = models.CharField(max_length=10)
    number = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.AVAILABLE)
    booking = models.ForeignKey(
        "bookings.Booking", null=True, blank=True, on_delete=models.SET_NULL, related_name="booked_seats"
    )
    hold = models.ForeignKey(
        "events.SeatHold", null=True, blank=True, on_delete=models.SET_NULL, related_name="seats"
    )
    held_until = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["section", "row_label", "number"]
        constraints = [
            models.UniqueConstraint(fields=["event", "row_label", "number"], name="unique_seat_per_event")
        ]
        indexes = [
            models.Index(fields=["event", "status"]),
        ]

    def __str__(self):
        return f"{self.section} {self.row_label}{self.number} ({self.event.title})"


class SeatHold(models.Model):
    """Temporary seat reservation: expires after N minutes unless converted to a booking.

    Concurrency safety comes from select_for_update() on Seat rows inside
    transaction.atomic() when creating a hold, plus the unique constraint that
    a seat can only be HELD by one live hold (enforced in code via row locks).
    """

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        CONVERTED = "converted", "Converted to booking"
        EXPIRED = "expired", "Expired"
        RELEASED = "released", "Released"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="seat_holds")
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="seat_holds")
    ticket_type = models.ForeignKey("events.TicketType", null=True, blank=True, on_delete=models.SET_NULL)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    expires_at = models.DateTimeField(db_index=True)
    booking = models.ForeignKey(
        "bookings.Booking", null=True, blank=True, on_delete=models.SET_NULL, related_name="holds"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["event", "status", "expires_at"])]

    def __str__(self):
        return f"Hold #{self.id} {self.event.title} ({self.status})"

    @property
    def is_live(self):
        from django.utils import timezone as _tz

        return self.status == self.Status.ACTIVE and _tz.now() <= self.expires_at


class Wishlist(models.Model):
    """An attendee's saved-for-later events."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wishlist")
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="wishlisted_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "event"], name="unique_wishlist_user_event")
        ]

    def __str__(self):
        return f"{self.user.email} ♥ {self.event.title}"


class Review(models.Model):
    """A 1–5 star rating plus optional comment, one per user per event."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews")
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "event"], name="unique_review_user_event")
        ]

    def __str__(self):
        return f"{self.rating}★ by {self.user.email} on {self.event.title}"
