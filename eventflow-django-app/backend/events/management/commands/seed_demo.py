from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import User
from events.models import Event, TicketType


class Command(BaseCommand):
    help = "Seed demo accounts and sample events for EventFlow."

    def handle(self, *args, **options):
        if User.objects.exists():
            self.stdout.write(self.style.WARNING("Users already exist -- skipping seed."))
            return

        admin = User.objects.create_user(
            username="admin@eventflow.dev", email="admin@eventflow.dev", password="password123",
            first_name="Ada", last_name="Admin", role="admin", is_staff=True, is_superuser=True,
        )
        organizer = User.objects.create_user(
            username="organizer@eventflow.dev", email="organizer@eventflow.dev", password="password123",
            first_name="Oli", last_name="Organizer", role="organizer",
        )
        User.objects.create_user(
            username="attendee@eventflow.dev", email="attendee@eventflow.dev", password="password123",
            first_name="Alex", last_name="Attendee", role="attendee",
        )

        now = timezone.now()

        def in_days(n):
            return now + timedelta(days=n)

        e1 = Event.objects.create(
            organizer=organizer, title="Night Frequencies: Open Air Festival",
            description="A dusk-till-dawn lineup of electronic acts across three outdoor stages.",
            category="Music", venue="Riverside Park", city="Austin",
            starts_at=in_days(21), ends_at=in_days(21), status="published",
        )
        TicketType.objects.create(event=e1, name="General Admission", price=65, quantity_total=200)
        TicketType.objects.create(event=e1, name="VIP", price=150, quantity_total=40)

        e2 = Event.objects.create(
            organizer=organizer, title="Build & Ship: Product Conference",
            description="A one-day conference for people who design, build, and launch products.",
            category="Conference", venue="Grand Convention Hall", city="Chicago",
            starts_at=in_days(40), ends_at=in_days(41), status="published",
        )
        TicketType.objects.create(event=e2, name="Standard Pass", price=249, quantity_total=150)
        TicketType.objects.create(event=e2, name="Student Pass", price=99, quantity_total=50)

        e3 = Event.objects.create(
            organizer=organizer, title="Comedy After Dark",
            description="Five stand-up comedians, one stage, way too many bad decisions retold.",
            category="Comedy", venue="The Blue Room", city="Austin",
            starts_at=in_days(9), ends_at=in_days(9), status="published",
        )
        TicketType.objects.create(event=e3, name="Door Ticket", price=25, quantity_total=80)

        self.stdout.write(self.style.SUCCESS("Seed complete. Demo accounts (password: password123):"))
        self.stdout.write("  Admin:     admin@eventflow.dev")
        self.stdout.write("  Organizer: organizer@eventflow.dev")
        self.stdout.write("  Attendee:  attendee@eventflow.dev")
