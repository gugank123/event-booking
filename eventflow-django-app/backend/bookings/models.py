import random
import string

from django.conf import settings
from django.db import models

from events.models import Event, TicketType


def generate_reference():
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "EVF-" + "".join(random.choice(chars) for _ in range(6))


class Booking(models.Model):
    class Status(models.TextChoices):
        PENDING_PAYMENT = "pending_payment", "Pending payment"
        CONFIRMED = "confirmed", "Confirmed"
        CANCELLED = "cancelled", "Cancelled"
        EXPIRED = "expired", "Expired"
        REFUNDED = "refunded", "Refunded"
        COMPLETED = "completed", "Completed"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bookings")
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="bookings")
    ticket_type = models.ForeignKey(TicketType, on_delete=models.CASCADE, related_name="bookings")
    quantity = models.PositiveIntegerField()
    # Money breakdown — all computed on the backend, never trusted from client.
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    platform_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    coupon = models.ForeignKey(
        "payments.Coupon", null=True, blank=True, on_delete=models.SET_NULL, related_name="bookings"
    )
    coupon_code = models.CharField(max_length=30, blank=True, default="")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING_PAYMENT)
    reference = models.CharField(max_length=20, unique=True, default=generate_reference, db_index=True)
    # Legacy mock-card fields kept for backwards compat with old rows; new
    # bookings go through Razorpay and leave these blank.
    payment_method = models.CharField(max_length=20, default="razorpay")
    card_last4 = models.CharField(max_length=4, blank=True, default="")
    seats = models.ManyToManyField("events.Seat", blank=True, related_name="bookings")
    hold = models.ForeignKey(
        "events.SeatHold", null=True, blank=True, on_delete=models.SET_NULL, related_name="bookings"
    )
    checked_in = models.BooleanField(default=False)
    checked_in_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status", "-created_at"]),
            models.Index(fields=["event", "status"]),
        ]

    def __str__(self):
        return f"{self.reference} — {self.event.title} x{self.quantity}"
