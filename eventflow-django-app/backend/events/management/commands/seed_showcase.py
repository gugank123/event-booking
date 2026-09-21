from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import User
from events.models import Event, Review, TicketType

# (title, description, category, venue, city, days_from_now, duration_hours, featured, [(ticket, price, qty)])
EVENTS = [
    (
        "Neon Pulse: Synthwave Night", "Analog synths, laser grids and retro-futurist visuals all night.",
        "Music", "The Echo Chamber", "Los Angeles", 5, 5, True,
        [("General Admission", 45, 150), ("VIP Deck", 120, 30)],
    ),
    (
        "Taste of Italy Food Festival", "Forty vendors, live pasta-making and a pizza championship.",
        "Food & Drink", "Harbor Park", "San Diego", 8, 9, True,
        [("Taster Pass", 35, 300), ("VIP Gourmet", 95, 60)],
    ),
    (
        "Startup Pitch Slam", "Twenty startups, five minutes each, one giant novelty cheque.",
        "Conference", "Innovation Hub", "Austin", 12, 6, False,
        [("Attendee", 49, 200), ("Founder VIP", 149, 40)],
    ),
    (
        "Shakespeare in the Park: Hamlet", "The classic tragedy under the stars, blankets encouraged.",
        "Theatre", "Greenfield Amphitheatre", "Portland", 15, 3, False,
        [("Lawn", 20, 400), ("Reserved Seat", 55, 120)],
    ),
    (
        "City Marathon 10K Fun Run", "A scenic riverside 10K with timing chips and finish-line brunch.",
        "Sports", "Riverside Start Line", "Chicago", 19, 4, False,
        [("Runner Entry", 30, 500), ("Runner + Tee", 45, 300)],
    ),
    (
        "Jazz & Wine Evening", "A smooth quartet paired with five local wine tastings.",
        "Music", "Vineyard Hall", "Napa", 23, 4, True,
        [("Standard", 60, 120), ("Reserve Table", 140, 20)],
    ),
    (
        "Indie Game Expo", "Play 80 unreleased indie games and meet the developers.",
        "Conference", "Pixel Convention Center", "Seattle", 27, 8, False,
        [("Day Pass", 25, 600), ("Weekend Pass", 60, 250)],
    ),
    (
        "Laugh Riot Comedy Tour", "Three national headliners, one night of chaos.",
        "Comedy", "Downtown Playhouse", "New York", 31, 3, False,
        [("General", 40, 250), ("Front Row", 85, 40)],
    ),
    (
        "Stargazing & Astrophotography Night", "Telescopes, expert guides and hot cocoa under dark skies.",
        "Outdoors", "Desert View Point", "Phoenix", 35, 5, False,
        [("General", 15, 200), ("Telescope Slot", 50, 25)],
    ),
]

REVIEWS = [
    # (event_title, user_email, rating, comment)
    ("Comedy After Dark", "attendee@eventflow.dev", 5, "Cried laughing. Best night out in months!"),
    ("Night Frequencies: Open Air Festival", "attendee@eventflow.dev", 4, "Great lineup, long bar queues."),
    ("Build & Ship: Product Conference", "organizer@eventflow.dev", 5, "Ran it myself - proud of this one."),
]


class Command(BaseCommand):
    help = "Add showcase demo events (idempotent) + a few sample reviews."

    def handle(self, *args, **options):
        organizer = User.objects.filter(role="organizer").first()
        if organizer is None:
            self.stdout.write(self.style.ERROR("No organizer account found. Run seed_demo first."))
            return
        now = timezone.now()
        added = 0
        for title, desc, cat, venue, city, days, hours, featured, tickets in EVENTS:
            event, created = Event.objects.get_or_create(
                title=title,
                defaults={
                    "organizer": organizer, "description": desc, "category": cat,
                    "venue": venue, "city": city,
                    "starts_at": now + timedelta(days=days),
                    "ends_at": now + timedelta(days=days, hours=hours),
                    "status": Event.Status.PUBLISHED, "is_featured": featured,
                },
            )
            if created:
                added += 1
                for name, price, qty in tickets:
                    TicketType.objects.create(event=event, name=name, price=price, quantity_total=qty)
        reviews = 0
        for title, email, rating, comment in REVIEWS:
            try:
                event = Event.objects.get(title=title)
                user = User.objects.get(email=email)
            except (Event.DoesNotExist, User.DoesNotExist):
                continue
            _, created = Review.objects.get_or_create(
                user=user, event=event, defaults={"rating": rating, "comment": comment}
            )
            reviews += created
        self.stdout.write(self.style.SUCCESS(f"Showcase seed complete: {added} events, {reviews} reviews."))
