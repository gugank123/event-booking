import secrets
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


class Payment(models.Model):
    """A Razorpay (or compatible gateway) payment attempt for one booking.

    The webhook / verify endpoints are the source of truth — never trust the
    frontend's claim that payment succeeded.
    """

    class Status(models.TextChoices):
        CREATED = "created", "Created"
        PENDING = "pending", "Pending"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"
        PARTIALLY_REFUNDED = "partially_refunded", "Partially refunded"

    booking = models.ForeignKey("bookings.Booking", on_delete=models.CASCADE, related_name="payments")
    gateway = models.CharField(max_length=20, default="razorpay")
    gateway_order_id = models.CharField(max_length=100, unique=True, db_index=True)
    gateway_payment_id = models.CharField(max_length=100, blank=True, default="", db_index=True)
    gateway_signature = models.CharField(max_length=255, blank=True, default="")
    amount = models.DecimalField(max_digits=10, decimal_places=2)  # INR
    currency = models.CharField(max_length=10, default="INR")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CREATED)
    raw_response = models.JSONField(default=dict, blank=True)
    # Idempotency: gateway event ids already processed for this payment.
    processed_events = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["booking", "status"])]

    def __str__(self):
        return f"{self.gateway_order_id} {self.amount} ({self.status})"


class Refund(models.Model):
    """Tracks gateway refund requests to completion — requested != succeeded."""

    class Status(models.TextChoices):
        REQUESTED = "requested", "Requested"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name="refunds")
    booking = models.ForeignKey("bookings.Booking", on_delete=models.CASCADE, related_name="refunds")
    gateway_refund_id = models.CharField(max_length=100, blank=True, default="")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.REQUESTED)
    reason = models.CharField(max_length=255, blank=True, default="")
    raw_response = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Refund {self.amount} for {self.booking.reference} ({self.status})"


class Coupon(models.Model):
    class DiscountType(models.TextChoices):
        PERCENT = "percent", "Percent"
        FLAT = "flat", "Flat"

    code = models.CharField(max_length=30, unique=True, db_index=True)
    discount_type = models.CharField(max_length=10, choices=DiscountType.choices)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    max_discount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    min_booking_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    starts_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    usage_limit = models.PositiveIntegerField(null=True, blank=True)
    per_user_limit = models.PositiveIntegerField(default=1)
    times_used = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return self.code

    def clean_code(self):
        self.code = self.code.strip().upper()

    def save(self, *args, **kwargs):
        self.clean_code()
        super().save(*args, **kwargs)

    def discount_for(self, subtotal: Decimal) -> Decimal:
        subtotal = Decimal(subtotal)
        if self.discount_type == self.DiscountType.PERCENT:
            amt = subtotal * self.discount_value / Decimal("100")
            if self.max_discount is not None:
                amt = min(amt, self.max_discount)
        else:
            amt = min(self.discount_value, subtotal)
        return amt.quantize(Decimal("0.01"))

    def validate_for(self, user, subtotal: Decimal):
        now = timezone.now()
        if not self.is_active:
            return "This coupon is no longer active."
        if self.starts_at and now < self.starts_at:
            return "This coupon is not valid yet."
        if self.expires_at and now > self.expires_at:
            return "This coupon has expired."
        if Decimal(subtotal) < self.min_booking_amount:
            return f"Minimum booking amount for this coupon is ₹{self.min_booking_amount}."
        if self.usage_limit is not None and self.times_used >= self.usage_limit:
            return "This coupon has reached its usage limit."
        used_by_user = CouponRedemption.objects.filter(coupon=self, user=user).count()
        if used_by_user >= self.per_user_limit:
            return "You have already used this coupon the maximum number of times."
        return None


class CouponRedemption(models.Model):
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name="redemptions")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="coupon_redemptions")
    booking = models.ForeignKey(
        "bookings.Booking", null=True, blank=True, on_delete=models.SET_NULL, related_name="coupon_redemptions"
    )
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["coupon", "user"])]

    def __str__(self):
        return f"{self.coupon.code} by {self.user.email} (-{self.discount_amount})"


def _ticket_number():
    return "TCK-" + secrets.token_hex(5).upper()


class Ticket(models.Model):
    """One ticket per seat (or per unit for general admission).

    QR payload is a signed opaque token (Ticket.qr_token), never personal or
    payment data. Verification marks USED exactly once.
    """

    class Status(models.TextChoices):
        VALID = "valid", "Valid"
        USED = "used", "Used"
        CANCELLED = "cancelled", "Cancelled"
        REFUNDED = "refunded", "Refunded"

    ticket_number = models.CharField(max_length=20, unique=True, default=_ticket_number, db_index=True)
    qr_token = models.CharField(max_length=64, unique=True, db_index=True, default="")
    booking = models.ForeignKey("bookings.Booking", on_delete=models.CASCADE, related_name="tickets")
    event = models.ForeignKey("events.Event", on_delete=models.CASCADE, related_name="tickets")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tickets")
    seat = models.ForeignKey("events.Seat", null=True, blank=True, on_delete=models.SET_NULL, related_name="tickets")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.VALID)
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["booking", "status"])]

    def __str__(self):
        return f"{self.ticket_number} ({self.status})"

    def save(self, *args, **kwargs):
        if not self.qr_token:
            self.qr_token = "QR-" + secrets.token_urlsafe(32)[:48]
        super().save(*args, **kwargs)
