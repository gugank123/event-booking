"""Tests for the Post Event / Create Event feature.

Run: python manage.py test events
Covers: permissions, drafts, preview, publish, booking incl. seats,
validation, cross-organizer protection, cancellation + notifications.
"""

from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import User
from bookings.models import Booking
from comms.models import Notification
from events.models import Event, Seat, TicketType


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class PostEventTests(APITestCase):
    def setUp(self):
        self.organizer = User.objects.create_user(
            username="org@eventflow.dev", email="org@eventflow.dev",
            password="password123", role=User.Role.ORGANIZER, email_verified=True,
        )
        self.other_org = User.objects.create_user(
            username="org2@eventflow.dev", email="org2@eventflow.dev",
            password="password123", role=User.Role.ORGANIZER, email_verified=True,
        )
        self.customer = User.objects.create_user(
            username="cust@eventflow.dev", email="cust@eventflow.dev",
            password="password123", role=User.Role.ATTENDEE, email_verified=True,
        )
        now = timezone.now()
        self.event = Event.objects.create(
            organizer=self.organizer, title="Live Draft", description="full info here",
            category="Music", venue="Hall", city="Austin",
            starts_at=now + timezone.timedelta(days=10),
            ends_at=now + timezone.timedelta(days=10, hours=3),
            status=Event.Status.PUBLISHED,
        )
        self.ticket = TicketType.objects.create(
            event=self.event, name="General", price=20, quantity_total=10, max_per_user=4
        )

    def auth(self, email):
        res = self.client.post(
            "/api/auth/login/", {"email": email, "password": "password123"}, format="json"
        )
        self.assertEqual(res.status_code, 200, res.content)
        return {"HTTP_AUTHORIZATION": f"Bearer {res.json()['access']}"}

    def confirm_booking(self, headers, booking_id):
        """Pay for a PENDING booking via the (keyless) test gateway path."""
        res = self.client.post("/api/payments/create-order/", {"booking_id": booking_id},
                               format="json", **headers)
        self.assertEqual(res.status_code, 201, res.content)
        order_id = res.json()["order_id"]
        res = self.client.post(
            "/api/payments/verify/",
            {"order_id": order_id, "payment_id": "pay_TEST_1", "signature": "test"},
            format="json", **headers)
        self.assertEqual(res.status_code, 200, res.content)

    def valid_payload(self, **over):
        now = timezone.now()
        payload = {
            "title": "New Night", "description": "A full description of the night.",
            "category": "Music", "venue": "Arena", "city": "Austin",
            "starts_at": (now + timezone.timedelta(days=20)).isoformat(),
            "ends_at": (now + timezone.timedelta(days=20, hours=4)).isoformat(),
            "status": "draft",
            "ticket_types": [{"name": "General", "price": "15.00", "quantity_total": 50}],
        }
        payload.update(over)
        return payload

    # Organizer can create (draft), customer cannot.
    def test_organizer_create_draft(self):
        res = self.client.post("/api/events/", self.valid_payload(),
                               format="json", **self.auth("org@eventflow.dev"))
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()["event"]["status"], "draft")

    def test_customer_cannot_create(self):
        res = self.client.post("/api/events/", self.valid_payload(),
                               format="json", **self.auth("cust@eventflow.dev"))
        self.assertEqual(res.status_code, 403)

    # Draft invisible publicly (list + direct URL), visible to owner (preview).
    def test_draft_hidden_publicly(self):
        self.event.status = Event.Status.DRAFT
        self.event.save()
        res = self.client.get("/api/events/")
        self.assertNotIn(self.event.id, [e["id"] for e in res.json()["events"]])
        res = self.client.get(f"/api/events/{self.event.id}/")
        self.assertEqual(res.status_code, 404)

    def test_owner_can_preview_draft(self):
        self.event.status = Event.Status.DRAFT
        self.event.save()
        res = self.client.get(f"/api/events/{self.event.id}/", **self.auth("org@eventflow.dev"))
        self.assertEqual(res.status_code, 200)

    # Publish makes it appear; customer can view + book; availability updates.
    def test_publish_view_book(self):
        o, c = self.auth("org@eventflow.dev"), self.auth("cust@eventflow.dev")
        res = self.client.put(f"/api/events/{self.event.id}/", {"status": "draft"}, format="json", **o)
        self.assertEqual(res.status_code, 200)
        res = self.client.put(f"/api/events/{self.event.id}/", {"status": "published"}, format="json", **o)
        self.assertEqual(res.status_code, 200)
        res = self.client.get("/api/events/")
        self.assertIn(self.event.id, [e["id"] for e in res.json()["events"]])
        res = self.client.post(
            "/api/bookings/",
            {"eventId": self.event.id, "ticketTypeId": self.ticket.id, "quantity": 2,
             "cardNumber": "4242424242424242", "expiry": "12/30", "cvc": "123"},
            format="json", **c,
        )
        self.assertEqual(res.status_code, 201)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.quantity_sold, 2)

    # Per-user cap enforced.
    def test_max_per_user(self):
        c = self.auth("cust@eventflow.dev")
        payload = lambda q: {"eventId": self.event.id, "ticketTypeId": self.ticket.id,
                             "quantity": q, "cardNumber": "4242424242424242",
                             "expiry": "12/30", "cvc": "123"}
        self.assertEqual(self.client.post("/api/bookings/", payload(4), format="json", **c).status_code, 201)
        res = self.client.post("/api/bookings/", payload(1), format="json", **c)
        self.assertEqual(res.status_code, 409)

    # Reserved seating: configure, pick seats, double-booking blocked.
    def test_reserved_seating_flow(self):
        o, c = self.auth("org@eventflow.dev"), self.auth("cust@eventflow.dev")
        res = self.client.post(
            f"/api/events/{self.event.id}/seats/",
            {"sections": [{"name": "VIP", "price": 100, "rows": ["A"], "seats_per_row": 2}]},
            format="json", **o,
        )
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(res.json()["seats_created"], 2)
        seats = list(Seat.objects.filter(event=self.event).values_list("id", flat=True))
        pay = lambda sids, headers: self.client.post(
            "/api/bookings/",
            {"eventId": self.event.id, "ticketTypeId": self.ticket.id, "seat_ids": sids,
             "cardNumber": "4242424242424242", "expiry": "12/30", "cvc": "123"},
            format="json", **headers)
        res = pay(seats, c)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(len(res.json()["booking"]["seats"]), 2)
        # Same seats again -> conflict.
        o2 = self.auth("org2@eventflow.dev")
        res = pay(seats, o2)
        self.assertEqual(res.status_code, 409)

    # Validation rejects bad data.
    def test_invalid_event_rejected(self):
        o = self.auth("org@eventflow.dev")
        bad = self.valid_payload(title="  ", ends_at=(timezone.now()).isoformat())
        res = self.client.post("/api/events/", bad, format="json", **o)
        self.assertEqual(res.status_code, 400)
        bad = self.valid_payload(ticket_types=[{"name": "x", "price": -5, "quantity_total": 10}])
        res = self.client.post("/api/events/", bad, format="json", **o)
        self.assertEqual(res.status_code, 400)

    # Cross-organizer edit blocked; customer edit blocked.
    def test_edit_permissions(self):
        o2 = self.auth("org2@eventflow.dev")
        res = self.client.put(f"/api/events/{self.event.id}/", {"title": "Hijack"}, format="json", **o2)
        self.assertEqual(res.status_code, 403)
        c = self.auth("cust@eventflow.dev")
        res = self.client.put(f"/api/events/{self.event.id}/", {"title": "Hijack"}, format="json", **c)
        self.assertEqual(res.status_code, 403)

    # Duplicate + delete-draft rules.
    def test_duplicate_and_delete(self):
        o = self.auth("org@eventflow.dev")
        res = self.client.post(f"/api/events/{self.event.id}/duplicate/", {}, format="json", **o)
        self.assertEqual(res.status_code, 201)
        dup_id = res.json()["event"]["id"]
        self.assertEqual(res.json()["event"]["status"], "draft")
        res = self.client.delete(f"/api/events/{dup_id}/", **o)
        self.assertEqual(res.status_code, 200)

    def test_cannot_delete_with_bookings(self):
        o, c = self.auth("org@eventflow.dev"), self.auth("cust@eventflow.dev")
        res = self.client.post(
            "/api/bookings/",
            {"eventId": self.event.id, "ticketTypeId": self.ticket.id, "quantity": 1},
            format="json", **c)
        self.assertEqual(res.status_code, 201)
        self.confirm_booking(c, res.json()["booking"]["id"])
        res = self.client.delete(f"/api/events/{self.event.id}/", **o)
        self.assertEqual(res.status_code, 409)

    # Cancellation notifies attendees.
    def test_cancel_notifies(self):
        o, c = self.auth("org@eventflow.dev"), self.auth("cust@eventflow.dev")
        res = self.client.post(
            "/api/bookings/",
            {"eventId": self.event.id, "ticketTypeId": self.ticket.id, "quantity": 1},
            format="json", **c)
        self.confirm_booking(c, res.json()["booking"]["id"])
        res = self.client.put(f"/api/events/{self.event.id}/", {"status": "cancelled"},
                              format="json", **o)
        self.assertEqual(res.status_code, 200)
        self.assertGreaterEqual(res.json()["notified"], 1)
        self.assertTrue(Notification.objects.filter(user=self.customer, category="EVENT").exists())

    # Booking window enforced.
    def test_booking_window(self):
        c = self.auth("cust@eventflow.dev")
        self.event.booking_opens_at = timezone.now() + timezone.timedelta(days=1)
        self.event.save()
        res = self.client.post(
            "/api/bookings/",
            {"eventId": self.event.id, "ticketTypeId": self.ticket.id, "quantity": 1,
             "cardNumber": "4242424242424242", "expiry": "12/30", "cvc": "123"},
            format="json", **c)
        self.assertEqual(res.status_code, 409)
