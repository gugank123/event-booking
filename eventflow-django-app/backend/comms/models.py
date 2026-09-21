import secrets

from django.conf import settings
from django.db import models


class Notification(models.Model):
    """In-app notification center entry. Email (if any) is sent alongside, not stored."""

    class Category(models.TextChoices):
        BOOKING = "BOOKING", "Booking"
        EVENT = "EVENT", "Event"
        INVITATION = "INVITATION", "Invitation"
        MESSAGE = "MESSAGE", "Message"
        PAYMENT = "PAYMENT", "Payment"
        SUPPORT = "SUPPORT", "Support"
        SYSTEM = "SYSTEM", "System"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.SYSTEM)
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=300, blank=True, default="")
    event = models.ForeignKey("events.Event", null=True, blank=True, on_delete=models.SET_NULL, related_name="notifications")
    booking = models.ForeignKey("bookings.Booking", null=True, blank=True, on_delete=models.SET_NULL, related_name="notifications")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_read", "-created_at"]),
        ]

    def __str__(self):
        return f"[{self.category}] {self.title} -> {self.user}"


class Conversation(models.Model):
    """A support-style thread between a customer and an organizer about an event/booking."""

    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        RESOLVED = "RESOLVED", "Resolved"
        CLOSED = "CLOSED", "Closed"

    class Topic(models.TextChoices):
        GENERAL = "general", "General enquiry"
        BOOKING = "booking", "Booking question"
        SEAT = "seat", "Seat question"
        EVENT_INFO = "event_info", "Event information"
        CANCELLATION = "cancellation", "Cancellation question"
        OTHER = "other", "Other"

    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="conversations")
    organizer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="handled_conversations")
    event = models.ForeignKey("events.Event", null=True, blank=True, on_delete=models.SET_NULL, related_name="conversations")
    booking = models.ForeignKey("bookings.Booking", null=True, blank=True, on_delete=models.SET_NULL, related_name="conversations")
    subject = models.CharField(max_length=200)
    topic = models.CharField(max_length=20, choices=Topic.choices, default=Topic.GENERAL)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["customer", "-updated_at"]),
            models.Index(fields=["organizer", "-updated_at"]),
        ]

    def __str__(self):
        return f"#{self.id} {self.subject} ({self.status})"


class ConversationMessage(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_messages")
    body = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"msg by {self.sender} in #{self.conversation_id}"


def generate_invite_token():
    return "INV-" + secrets.token_urlsafe(18)[:24]


class Invitation(models.Model):
    """An organizer's invitation of a (registered or not-yet-registered) guest to an event."""

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        ACCEPTED = "ACCEPTED", "Accepted"
        DECLINED = "DECLINED", "Declined"
        EXPIRED = "EXPIRED", "Expired"

    event = models.ForeignKey("events.Event", on_delete=models.CASCADE, related_name="invitations")
    invited_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_invitations")
    invitee = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="invitations"
    )
    email = models.EmailField()
    message = models.TextField(blank=True, default="")
    token = models.CharField(max_length=32, unique=True, default=generate_invite_token)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    expires_at = models.DateTimeField(null=True, blank=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["token"]),
            models.Index(fields=["email", "status"]),
        ]

    def __str__(self):
        return f"Invite {self.email} -> {self.event} ({self.status})"


class Announcement(models.Model):
    """An organizer broadcast about one event (venue change, postponement, reminder...)."""

    event = models.ForeignKey("events.Event", on_delete=models.CASCADE, related_name="announcements")
    organizer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="announcements")
    title = models.CharField(max_length=200)
    message = models.TextField()
    send_email = models.BooleanField(default=True)
    send_in_app = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.event})"


class SupportTicket(models.Model):
    """A customer-care ticket filed by a user, answered by admins/support staff."""

    class Category(models.TextChoices):
        BOOKING = "booking", "Booking"
        TICKETS = "tickets", "Tickets"
        SEATS = "seats", "Seat selection"
        PAYMENTS = "payments", "Payments"
        CANCELLATION = "cancellation", "Cancellation"
        REFUNDS = "refunds", "Refunds"
        ACCOUNT = "account", "Account"
        EVENTS = "events", "Events"
        ORGANIZER = "organizer", "Organizer issues"
        TECHNICAL = "technical", "Technical problems"
        OTHER = "other", "Other"

    class Priority(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"
        URGENT = "URGENT", "Urgent"

    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        WAITING_FOR_USER = "WAITING_FOR_USER", "Waiting for user"
        RESOLVED = "RESOLVED", "Resolved"
        CLOSED = "CLOSED", "Closed"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="support_tickets")
    subject = models.CharField(max_length=200)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.OTHER)
    description = models.TextField()
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.MEDIUM)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="assigned_tickets"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["user", "-updated_at"]),
            models.Index(fields=["status", "-updated_at"]),
        ]

    def __str__(self):
        return f"#{self.id} {self.subject} ({self.status})"


class SupportMessage(models.Model):
    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="support_messages")
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"reply by {self.sender} on ticket #{self.ticket_id}"


class FAQ(models.Model):
    category = models.CharField(max_length=60)
    question = models.CharField(max_length=300)
    answer = models.TextField()
    order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category", "order", "id"]

    def __str__(self):
        return f"[{self.category}] {self.question}"


class Report(models.Model):
    """A user-filed problem report (event/organizer/booking/payment/technical/other)."""

    class Category(models.TextChoices):
        EVENT = "event", "Event problem"
        ORGANIZER = "organizer", "Organizer problem"
        BOOKING = "booking", "Booking problem"
        PAYMENT = "payment", "Payment problem"
        TECHNICAL = "technical", "Technical problem"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        RESOLVED = "RESOLVED", "Resolved"
        CLOSED = "CLOSED", "Closed"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reports")
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.OTHER)
    subject = models.CharField(max_length=200)
    description = models.TextField()
    event = models.ForeignKey("events.Event", null=True, blank=True, on_delete=models.SET_NULL, related_name="reports")
    booking = models.ForeignKey("bookings.Booking", null=True, blank=True, on_delete=models.SET_NULL, related_name="reports")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["status", "-created_at"]),
        ]

    def __str__(self):
        return f"[{self.category}] {self.subject} ({self.status})"
