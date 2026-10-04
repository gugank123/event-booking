"""Send event reminders (24h) + mark completed events. Run hourly via cron."""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = "Send 24h event reminders and mark past events completed."

    def handle(self, *args, **options):
        from bookings.models import Booking
        from comms.services import notify_user
        from comms.emails import send_email
        from events.models import Event

        now = timezone.now()
        window_start = now + timedelta(hours=23)
        window_end = now + timedelta(hours=25)
        events = Event.objects.filter(status=Event.Status.PUBLISHED,
                                      starts_at__gte=window_start, starts_at__lt=window_end)
        sent = 0
        for event in events:
            bookings = Booking.objects.filter(event=event, status=Booking.Status.CONFIRMED
                                              ).select_related("user")
            for b in bookings:
                notify_user(b.user, f"Reminder: {event.title} is tomorrow",
                            f"{event.title} starts {event.starts_at:%b %d, %I:%M %p} at {event.venue}. Ref {b.reference}.",
                            category="EVENT", link=f"/events/{event.id}", event=event, booking=b)
                send_email(b.user.email, f"Reminder: {event.title} is tomorrow", "event_update",
                           {"user": b.user, "event": event, "changes": ["Your event starts in ~24 hours. See you there!"]})
                sent += 1
        done = Event.objects.filter(status__in=["published", "sold_out"], ends_at__lt=now
                                    ).update(status=Event.Status.COMPLETED)
        self.stdout.write(self.style.SUCCESS(f"Reminded {sent} booking(s); completed {done} event(s)."))
