"""Shared helpers: in-app notifications (+ optional email) and event-change fan-out."""

from .emails import send_event_update_email, send_organizer_message_email
from .models import Notification


def notify_user(user, title, message, category=Notification.Category.SYSTEM,
                link="", event=None, booking=None, send_email=False,
                email_subject=None, email_body=None):
    """Create an in-app notification, optionally also sending an email."""
    note = Notification.objects.create(
        user=user, category=category, title=title, message=message,
        link=link, event=event, booking=booking,
    )
    if send_email:
        send_organizer_message_email(
            user, email_subject or title, email_body or message,
            event=event, booking=booking,
        )
    return note


def notify_event_attendees(event, title, message, category=Notification.Category.EVENT,
                           send_email=True, link=""):
    """Notify every user with a confirmed booking for `event`. Returns count."""
    from bookings.models import Booking

    user_ids = (
        Booking.objects.filter(event=event, status=Booking.Status.CONFIRMED)
        .values_list("user_id", flat=True).distinct()
    )
    from accounts.models import User

    count = 0
    for user in User.objects.filter(id__in=user_ids):
        notify_user(user, title, message, category=category, link=link or f"/events/{event.id}",
                    event=event, send_email=send_email)
        count += 1
    return count


def notify_event_change(event, changes, send_email=True):
    """Fan out date/venue/cancellation changes to confirmed attendees."""
    if not changes:
        return 0
    from bookings.models import Booking

    recipients = (
        Booking.objects.filter(event=event, status=Booking.Status.CONFIRMED)
        .select_related("user").order_by("id")
    )
    seen, count = set(), 0
    for booking in recipients:
        if booking.user_id in seen:
            continue
        seen.add(booking.user_id)
        Notification.objects.create(
            user=booking.user,
            category=Notification.Category.EVENT,
            title=f"Update for {event.title}",
            message="; ".join(changes),
            link=f"/events/{event.id}",
            event=event,
            booking=booking,
        )
        if send_email:
            send_event_update_email(booking.user, event, changes)
        count += 1
    return count
