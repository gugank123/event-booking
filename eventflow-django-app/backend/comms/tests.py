"""Workflow tests for auth, events, bookings and the comms system.

Run: python manage.py test
"""

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import User
from bookings.models import Booking
from comms.models import Conversation, Invitation, Notification, SupportTicket
from events.models import Event, TicketType


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class PlatformTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin@eventflow.dev", email="admin@eventflow.dev",
            password="password123", role=User.Role.ADMIN,
            first_name="Ada", last_name="Admin",
        )
        self.organizer = User.objects.create_user(
            username="organizer@eventflow.dev", email="organizer@eventflow.dev",
            password="password123", role=User.Role.ORGANIZER,
            first_name="Oli", last_name="Organizer",
        )
        self.attendee = User.objects.create_user(
            username="attendee@eventflow.dev", email="attendee@eventflow.dev",
            password="password123", role=User.Role.ATTENDEE,
            first_name="Alex", last_name="Attendee",
        )
        self.other = User.objects.create_user(
            username="other@eventflow.dev", email="other@eventflow.dev",
            password="password123", role=User.Role.ATTENDEE,
        )
        now = timezone.now()
        self.event = Event.objects.create(
            organizer=self.organizer, title="Test Fest", description="d",
            category="Music", venue="Hall", city="Austin",
            starts_at=now + timezone.timedelta(days=7),
            ends_at=now + timezone.timedelta(days=7, hours=3),
            status=Event.Status.PUBLISHED,
        )
        self.ticket = TicketType.objects.create(
            event=self.event, name="General", price=20, quantity_total=10
        )

    def auth(self, email):
        res = self.client.post(
            "/api/auth/login/", {"email": email, "password": "password123"}, format="json"
        )
        self.assertEqual(res.status_code, 200, res.content)
        return {"HTTP_AUTHORIZATION": f"Bearer {res.json()['access']}"}

    def book(self, headers, qty=1):
        return self.client.post(
            "/api/bookings/",
            {"eventId": self.event.id, "ticketTypeId": self.ticket.id, "quantity": qty,
             "cardNumber": "4242424242424242", "expiry": "12/30", "cvc": "123"},
            format="json", **headers,
        )

    # 1-2. registration + login
    def test_register_and_login(self):
        res = self.client.post(
            "/api/auth/register/",
            {"name": "Nina New", "email": "nina@eventflow.dev",
             "password": "supersecret1", "role": "attendee"},
            format="json",
        )
        self.assertEqual(res.status_code, 201)
        self.assertIn("access", res.json())
        res = self.client.post(
            "/api/auth/login/",
            {"email": "nina@eventflow.dev", "password": "supersecret1"}, format="json",
        )
        self.assertEqual(res.status_code, 200)

    # 3. organizer permissions
    def test_attendee_cannot_create_event(self):
        res = self.client.post(
            "/api/events/", {"title": "x", "category": "Music", "venue": "v",
                             "city": "c", "starts_at": "2027-01-01T10:00:00Z",
                             "ends_at": "2027-01-01T12:00:00Z", "ticket_types": []},
            format="json", **self.auth("attendee@eventflow.dev"),
        )
        self.assertEqual(res.status_code, 403)

    def test_organizer_cannot_edit_others_event(self):
        other_org = User.objects.create_user(
            username="org2@eventflow.dev", email="org2@eventflow.dev",
            password="password123", role=User.Role.ORGANIZER,
        )
        self.client.force_authenticate(user=other_org)
        res = self.client.put(f"/api/events/{self.event.id}/", {"title": "Hijacked"}, format="json")
        self.assertEqual(res.status_code, 403)

    # 4. event creation
    def test_organizer_can_create_event(self):
        res = self.client.post(
            "/api/events/",
            {"title": "New Night", "category": "Music", "venue": "Hall", "city": "Austin",
             "starts_at": "2027-02-01T10:00:00Z", "ends_at": "2027-02-01T12:00:00Z",
             "ticket_types": [{"name": "General", "price": "15.00", "quantity_total": 50}]},
            format="json", **self.auth("organizer@eventflow.dev"),
        )
        self.assertEqual(res.status_code, 201)

    # 5-6. booking + ticket-type (seat) selection limits
    def test_booking_and_oversell(self):
        a = self.auth("attendee@eventflow.dev")
        res = self.book(a, qty=2)
        self.assertEqual(res.status_code, 201)
        res = self.book(a, qty=999)
        self.assertEqual(res.status_code, 409)

    # 7. organizer -> user message (broadcast)
    def test_broadcast_to_attendees(self):
        a, o = self.auth("attendee@eventflow.dev"), self.auth("organizer@eventflow.dev")
        self.assertEqual(self.book(a).status_code, 201)
        res = self.client.post(
            "/api/comms/broadcast/",
            {"event_id": self.event.id, "audience": "event",
             "subject": "Tomorrow!", "body": "Starts at 6pm.", "send_email": False},
            format="json", **o,
        )
        self.assertEqual(res.status_code, 201)
        self.assertGreaterEqual(res.json()["sent"], 1)
        self.assertTrue(
            Notification.objects.filter(user=self.attendee, category="MESSAGE", title="Tomorrow!").exists()
        )

    # 8. user -> organizer conversation
    def test_conversation_thread(self):
        a, o = self.auth("attendee@eventflow.dev"), self.auth("organizer@eventflow.dev")
        res = self.client.post(
            "/api/comms/conversations/",
            {"event_id": self.event.id, "subject": "Seat Q", "topic": "seat", "body": "Can I switch?"},
            format="json", **a,
        )
        self.assertEqual(res.status_code, 201)
        cid = res.json()["conversation"]["id"]
        res = self.client.post(f"/api/comms/conversations/{cid}/", {"body": "Sure."}, format="json", **o)
        self.assertEqual(res.status_code, 201)
        res = self.client.get(f"/api/comms/conversations/{cid}/", **a)
        self.assertEqual(len(res.json()["messages"]), 2)

    # 9-10. invitation create + accept
    def test_invitation_flow(self):
        o, a = self.auth("organizer@eventflow.dev"), self.auth("attendee@eventflow.dev")
        res = self.client.post(
            "/api/comms/invitations/",
            {"event_id": self.event.id, "email": "attendee@eventflow.dev", "message": "Come!"},
            format="json", **o,
        )
        self.assertEqual(res.status_code, 201)
        token = res.json()["invitation"]["token"]
        res = self.client.post(f"/api/comms/invitations/{token}/accept/", {}, format="json", **a)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            Invitation.objects.get(token=token).status, Invitation.Status.ACCEPTED
        )

    # 11-12. booking notification + mark read
    def test_booking_notification_and_read(self):
        from django.core import mail

        a = self.auth("attendee@eventflow.dev")
        self.assertEqual(self.book(a).status_code, 201)
        self.assertEqual(len(mail.outbox), 1)  # confirmation email
        note = Notification.objects.filter(user=self.attendee, category="BOOKING").first()
        self.assertIsNotNone(note)
        res = self.client.get("/api/comms/notifications/unread-count/", **a)
        self.assertGreaterEqual(res.json()["unread"], 1)
        res = self.client.post(f"/api/comms/notifications/{note.id}/read/", {}, format="json", **a)
        self.assertTrue(res.json()["notification"]["is_read"])

    # 13-14. support ticket + reply
    def test_support_ticket_flow(self):
        a, d = self.auth("attendee@eventflow.dev"), self.auth("admin@eventflow.dev")
        res = self.client.post(
            "/api/comms/support/",
            {"subject": "Help", "category": "booking", "description": "?", "priority": "HIGH"},
            format="json", **a,
        )
        self.assertEqual(res.status_code, 201)
        tid = res.json()["ticket"]["id"]
        res = self.client.post(f"/api/comms/support/{tid}/", {"body": "On it."}, format="json", **d)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(SupportTicket.objects.get(pk=tid).status, SupportTicket.Status.IN_PROGRESS)

    # 15. event cancellation notifies attendees
    def test_cancellation_notifies(self):
        a, o = self.auth("attendee@eventflow.dev"), self.auth("organizer@eventflow.dev")
        self.assertEqual(self.book(a).status_code, 201)
        res = self.client.put(
            f"/api/events/{self.event.id}/", {"status": "cancelled"}, format="json", **o
        )
        self.assertEqual(res.status_code, 200)
        self.assertGreaterEqual(res.json()["notified"], 1)
        self.assertTrue(
            Notification.objects.filter(user=self.attendee, category="EVENT").exists()
        )

    # 16. unauthorized access prevention
    def test_idor_blocked(self):
        a = self.auth("attendee@eventflow.dev")
        booking = Booking.objects.create(
            user=self.other, event=self.event, ticket_type=self.ticket,
            quantity=1, total_amount=20, card_last4="4242",
        )
        # cannot cancel someone else's booking
        res = self.client.post(f"/api/bookings/{booking.id}/cancel/", {}, format="json", **a)
        self.assertEqual(res.status_code, 403)
        # cannot read someone else's conversation
        conv = Conversation.objects.create(
            customer=self.other, organizer=self.organizer,
            event=self.event, subject="x", topic="general",
        )
        res = self.client.get(f"/api/comms/conversations/{conv.id}/", **a)
        self.assertEqual(res.status_code, 403)
        # attendee cannot use admin-only support list semantics for others' tickets
        other_headers = self.auth("other@eventflow.dev")
        t = self.client.post(
            "/api/comms/support/",
            {"subject": "priv", "category": "other", "description": "x"}, format="json", **other_headers,
        ).json()["ticket"]["id"]
        res = self.client.get(f"/api/comms/support/{t}/", **a)
        self.assertEqual(res.status_code, 403)
