from decimal import Decimal

from django.core.management.base import BaseCommand

from events.models import Event

SAMPLE_EVENTS = [
    {
        "title": "Tech Innovators Conference 2026",
        "description": (
            "A technology conference featuring talks, workshops "
            "and networking sessions."
        ),
        "category": "Technology",
        "date": "2026-09-15",
        "time": "10:00:00",
        "venue": "JJCET Auditorium",
        "price": Decimal("500.00"),
    },
    {
        "title": "Campus Music Festival 2026",
        "description": (
            "A live music event featuring student bands and guest performers."
        ),
        "category": "Music",
        "date": "2026-09-20",
        "time": "18:00:00",
        "venue": "College Open Ground",
        "price": Decimal("300.00"),
    },
    {
        "title": "Entrepreneurship Summit 2026",
        "description": (
            "A business and entrepreneurship event for students "
            "and young professionals."
        ),
        "category": "Business",
        "date": "2026-09-25",
        "time": "09:30:00",
        "venue": "Seminar Hall",
        "price": Decimal("400.00"),
    },
]


class Command(BaseCommand):
    help = "Load the three sample events for Week 1."

    def handle(self, *args, **options):
        created = 0
        for data in SAMPLE_EVENTS:
            event, was_created = Event.objects.get_or_create(
                title=data["title"],
                defaults=data,
            )
            if was_created:
                created += 1
                self.stdout.write(self.style.SUCCESS(f"Created: {event.title}"))
            else:
                self.stdout.write(f"Skipped (already exists): {event.title}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. {created} new event(s) created. "
                f"Total events in database: {Event.objects.count()}"
            )
        )
