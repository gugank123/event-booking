"""Reusable email service for the whole platform.

All mail goes through Django's email framework (configured via
EMAIL_* env vars; console backend by default in development).
Every sender wraps delivery so a mail failure never breaks the request.
"""

import logging

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def send_email(to_email, subject, template_base, context, fail_silently=True):
    """Render comms/emails/<template_base>.txt (+ .html) and send.

    Returns True if handed to the backend without error.
    """
    if not to_email:
        return False
    ctx = {"frontend_url": settings.FRONTEND_URL, "support_email": settings.SUPPORT_EMAIL, **context}
    try:
        text_body = render_to_string(f"comms/emails/{template_base}.txt", ctx)
        try:
            html_body = render_to_string(f"comms/emails/{template_base}.html", ctx)
        except Exception:
            html_body = None
        send_mail(
            subject=subject,
            message=text_body,
            from_email=None,
            recipient_list=[to_email],
            html_message=html_body,
            fail_silently=fail_silently,
        )
        return True
    except Exception:
        logger.exception("Failed to send '%s' email to %s", template_base, to_email)
        return False


def send_welcome_email(user):
    return send_email(
        user.email,
        "Welcome to EventFlow",
        "welcome",
        {"user": user},
    )


def send_booking_confirmation_email(user, booking, event, ticket_type):
    return send_email(
        user.email,
        f"You're going to {event.title} - {booking.reference}",
        "booking_confirmation",
        {"user": user, "booking": booking, "event": event, "ticket_type": ticket_type},
    )


def send_booking_cancellation_email(user, booking, event):
    return send_email(
        user.email,
        f"Booking {booking.reference} cancelled",
        "booking_cancellation",
        {"user": user, "booking": booking, "event": event},
    )


def send_invitation_email(invitation):
    return send_email(
        invitation.email,
        f"You're invited: {invitation.event.title}",
        "invitation",
        {"invitation": invitation, "event": invitation.event},
    )


def send_announcement_email(user, announcement):
    return send_email(
        user.email,
        f"{announcement.event.title}: {announcement.title}",
        "announcement",
        {"user": user, "announcement": announcement, "event": announcement.event},
    )


def send_organizer_message_email(user, subject, body, event=None, booking=None):
    return send_email(
        user.email,
        subject,
        "organizer_message",
        {"user": user, "subject": subject, "body": body, "event": event, "booking": booking},
    )


def send_support_update_email(user, ticket, reply_body=None):
    return send_email(
        user.email,
        f"Support ticket #{ticket.id}: {ticket.status}",
        "support_update",
        {"user": user, "ticket": ticket, "reply_body": reply_body},
    )


def send_event_update_email(user, event, changes):
    """`changes` is a list of human-readable strings, e.g. 'Venue: A -> B'."""
    return send_email(
        user.email,
        f"Update for {event.title}",
        "event_update",
        {"user": user, "event": event, "changes": changes},
    )
