from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from .models import Event


class EventModelTests(TestCase):
    def setUp(self):
        self.event = Event.objects.create(
            title="Tech Innovators Conference 2026",
            description="A technology conference featuring talks, "
                        "workshops and networking sessions.",
            category="Technology",
            date="2026-09-15",
            time="10:00:00",
            venue="JJCET Auditorium",
            price=Decimal("500.00"),
        )

    def test_event_is_saved_to_database(self):
        self.assertEqual(Event.objects.count(), 1)

    def test_event_string_representation(self):
        self.assertEqual(str(self.event), "Tech Innovators Conference 2026")

    def test_price_is_stored_as_decimal(self):
        self.assertIsInstance(self.event.price, Decimal)
        self.assertEqual(self.event.price, Decimal("500.00"))


class EventListViewTests(TestCase):
    def setUp(self):
        Event.objects.create(
            title="Tech Innovators Conference 2026",
            description="A technology conference.",
            category="Technology",
            date="2026-09-15",
            time="10:00:00",
            venue="JJCET Auditorium",
            price="500.00",
        )
        Event.objects.create(
            title="Campus Music Festival 2026",
            description="A live music event.",
            category="Music",
            date="2026-09-20",
            time="18:00:00",
            venue="College Open Ground",
            price="300.00",
        )

    def test_event_list_returns_200(self):
        response = self.client.get(reverse("event_list"))
        self.assertEqual(response.status_code, 200)

    def test_event_list_uses_correct_template(self):
        response = self.client.get(reverse("event_list"))
        self.assertTemplateUsed(response, "events/event_list.html")

    def test_event_list_shows_database_events(self):
        response = self.client.get(reverse("event_list"))
        self.assertContains(response, "Tech Innovators Conference 2026")
        self.assertContains(response, "Campus Music Festival 2026")
        self.assertContains(response, "JJCET Auditorium")

    def test_event_list_orders_by_date(self):
        response = self.client.get(reverse("event_list"))
        titles = list(response.context["events"].values_list("title", flat=True))
        self.assertEqual(
            titles,
            ["Tech Innovators Conference 2026", "Campus Music Festival 2026"],
        )

    def test_empty_event_list_shows_friendly_message(self):
        Event.objects.all().delete()
        response = self.client.get(reverse("event_list"))
        self.assertContains(response, "No upcoming events available.")
