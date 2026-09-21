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
        CONFIRMED = "confirmed", "Confirmed"
        CANCELLED = "cancelled", "Cancelled"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bookings")
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="bookings")
    ticket_type = models.ForeignKey(TicketType, on_delete=models.CASCADE, related_name="bookings")
    quantity = models.PositiveIntegerField()
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CONFIRMED)
    reference = models.CharField(max_length=20, unique=True, default=generate_reference)
    payment_method = models.CharField(max_length=20, default="mock-card")
    card_last4 = models.CharField(max_length=4)
    checked_in = models.BooleanField(default=False)
    checked_in_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.reference} — {self.event.title} x{self.quantity}"
