from datetime import timedelta

from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bookings.models import Booking
from events.models import Event

from .emails import (
    send_invitation_email,
    send_organizer_message_email,
    send_support_update_email,
)
from .models import (
    Announcement,
    Conversation,
    ConversationMessage,
    FAQ,
    Invitation,
    Notification,
    Report,
    SupportMessage,
    SupportTicket,
)
from .serializers import (
    AnnouncementSerializer,
    BroadcastSerializer,
    ConversationCreateSerializer,
    ConversationMessageSerializer,
    ConversationSerializer,
    FAQSerializer,
    InvitationCreateSerializer,
    InvitationSerializer,
    NotificationSerializer,
    ReportSerializer,
    SupportMessageSerializer,
    SupportTicketCreateSerializer,
    SupportTicketSerializer,
)
from .services import notify_event_attendees, notify_user


def can_manage_event(user, event):
    return user.role == "admin" or event.organizer_id == user.id


def is_admin(user):
    return user.is_authenticated and user.role == "admin"


# ---------------- Notifications ----------------

class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        notes = Notification.objects.filter(user=request.user).select_related("event", "booking")
        if request.query_params.get("unread") == "true":
            notes = notes.filter(is_read=False)
        category = request.query_params.get("category")
        if category:
            notes = notes.filter(category=category.upper())
        notes = notes[:100]
        return Response({"notifications": NotificationSerializer(notes, many=True).data})


class NotificationUnreadCountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"unread": Notification.objects.filter(user=request.user, is_read=False).count()})


class NotificationReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        note = get_object_or_404(Notification, pk=pk, user=request.user)
        note.is_read = True
        note.save(update_fields=["is_read"])
        return Response({"notification": NotificationSerializer(note).data})


class NotificationReadAllView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        updated = Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({"marked": updated})


class NotificationDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        note = get_object_or_404(Notification, pk=pk, user=request.user)
        note.delete()
        return Response({"ok": True})


# ---------------- Organizer broadcast ----------------

class BroadcastView(APIView):
    """Organizer message to event attendees (all) or selected customers."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = BroadcastSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        event = get_object_or_404(Event, pk=data["event_id"])
        if not can_manage_event(request.user, event):
            raise PermissionDenied("You can only message attendees of your own events.")

        if data["audience"] == "event":
            recipients = (
                Booking.objects.filter(event=event, status=Booking.Status.CONFIRMED)
                .select_related("user").order_by("id")
            )
            users = []
            seen = set()
            for booking in recipients:
                if booking.user_id not in seen:
                    seen.add(booking.user_id)
                    users.append((booking.user, booking))
        else:
            from accounts.models import User

            users = [(u, None) for u in User.objects.filter(id__in=data["user_ids"])]
            if len(users) != len(set(data["user_ids"])):
                return Response({"error": "One or more selected users were not found."}, status=404)

        sent = 0
        for user, booking in users:
            Notification.objects.create(
                user=user,
                category=Notification.Category.MESSAGE,
                title=data["subject"],
                message=data["body"],
                link=f"/events/{event.id}",
                event=event,
                booking=booking,
            )
            if data["send_email"]:
                send_organizer_message_email(user, data["subject"], data["body"], event=event, booking=booking)
            sent += 1
        return Response({"sent": sent}, status=201)


# ---------------- Conversations (customer <-> organizer) ----------------

def serialize_conversation(conv, request):
    messages = conv.messages.select_related("sender").order_by("created_at")
    return {
        "conversation": ConversationSerializer(conv, context={"request": request}).data,
        "messages": ConversationMessageSerializer(messages, many=True, context={"request": request}).data,
    }


class ConversationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        convs = (
            Conversation.objects.filter(Q(customer=request.user) | Q(organizer=request.user))
            .select_related("customer", "organizer", "event", "booking__event")
            .order_by("-updated_at")
        )
        return Response(
            {"conversations": ConversationSerializer(convs, many=True, context={"request": request}).data}
        )

    def post(self, request):
        serializer = ConversationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        event = get_object_or_404(Event, pk=data["event_id"])
        booking = None
        if data.get("booking_id"):
            booking = get_object_or_404(Booking, pk=data["booking_id"], user=request.user, event=event)

        conv = Conversation.objects.create(
            customer=request.user,
            organizer=event.organizer,
            event=event,
            booking=booking,
            subject=data["subject"],
            topic=data["topic"],
        )
        ConversationMessage.objects.create(conversation=conv, sender=request.user, body=data["body"])
        notify_user(
            event.organizer,
            f"New enquiry: {data['subject']}",
            f"{request.user.email} wrote about {event.title}.",
            category=Notification.Category.MESSAGE,
            link=f"/organizer/conversations/{conv.id}",
            event=event,
        )
        return Response(serialize_conversation(conv, request), status=201)


class ConversationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_conversation(self, request, pk):
        conv = get_object_or_404(
            Conversation.objects.select_related("customer", "organizer", "event", "booking"), pk=pk
        )
        if not (conv.customer_id == request.user.id or conv.organizer_id == request.user.id or is_admin(request.user)):
            raise PermissionDenied("You don't have access to this conversation.")
        return conv

    def get(self, request, pk):
        conv = self.get_conversation(request, pk)
        # Reading the thread marks the other party's messages as read.
        conv.messages.exclude(sender=request.user).filter(is_read=False).update(is_read=True)
        return Response(serialize_conversation(conv, request))

    def post(self, request, pk):
        """Reply. `action` may be 'reply' (default) or 'status' ({status})."""
        conv = self.get_conversation(request, pk)
        if conv.status == Conversation.Status.CLOSED:
            return Response({"error": "This conversation is closed."}, status=409)

        if request.data.get("action") == "status":
            new_status = (request.data.get("status") or "").upper()
            if new_status not in Conversation.Status.values:
                return Response({"error": "Invalid status."}, status=400)
            if new_status != Conversation.Status.CLOSED and not (
                conv.organizer_id == request.user.id or is_admin(request.user)
            ):
                raise PermissionDenied("Only the organizer can change this status.")
            conv.status = new_status
            conv.save(update_fields=["status", "updated_at"])
            return Response(serialize_conversation(conv, request))

        body = (request.data.get("body") or "").strip()
        if not body:
            return Response({"error": "Message body is required."}, status=400)
        msg = ConversationMessage.objects.create(conversation=conv, sender=request.user, body=body)
        conv.status = Conversation.Status.IN_PROGRESS
        conv.save(update_fields=["status", "updated_at"])
        other = conv.organizer if request.user.id == conv.customer_id else conv.customer
        notify_user(
            other,
            f"New reply: {conv.subject}",
            body[:200],
            category=Notification.Category.MESSAGE,
            link=f"/messages/{conv.id}",
            event=conv.event,
            booking=conv.booking,
        )
        return Response(
            {"message": ConversationMessageSerializer(msg, context={"request": request}).data},
            status=201,
        )


# ---------------- Announcements ----------------

class AnnouncementListCreateView(APIView):
    def get_permissions(self):
        # Anyone can read an event's announcements; only organizers post them.
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAuthenticated()]

    def get(self, request, event_id):
        event = get_object_or_404(Event, pk=event_id)
        items = Announcement.objects.filter(event=event).order_by("-created_at")[:20]
        return Response({"announcements": AnnouncementSerializer(items, many=True).data})

    def post(self, request):
        serializer = AnnouncementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        event = get_object_or_404(Event, pk=serializer.validated_data["event"].id)
        if not can_manage_event(request.user, event):
            raise PermissionDenied("You can only post announcements for your own events.")
        announcement = Announcement.objects.create(organizer=request.user, **serializer.validated_data)
        notified = 0
        if announcement.send_in_app or announcement.send_email:
            # Reuse the attendee fan-out, honouring the channel flags.
            from bookings.models import Booking as BookingModel

            recipients = (
                BookingModel.objects.filter(event=event, status=BookingModel.Status.CONFIRMED)
                .select_related("user").order_by("id")
            )
            seen = set()
            for booking in recipients:
                if booking.user_id in seen:
                    continue
                seen.add(booking.user_id)
                if announcement.send_in_app:
                    Notification.objects.create(
                        user=booking.user,
                        category=Notification.Category.EVENT,
                        title=f"{event.title}: {announcement.title}",
                        message=announcement.message,
                        link=f"/events/{event.id}",
                        event=event,
                        booking=booking,
                    )
                if announcement.send_email:
                    from .emails import send_announcement_email

                    send_announcement_email(booking.user, announcement)
                notified += 1
        return Response(
            {"announcement": AnnouncementSerializer(announcement).data, "notified": notified},
            status=201,
        )


# ---------------- Invitations ----------------

class InvitationCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = InvitationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        event = get_object_or_404(Event, pk=data["event_id"])
        if not can_manage_event(request.user, event):
            raise PermissionDenied("You can only invite guests to your own events.")

        email = (data.get("email") or "").strip().lower()
        invitee = None
        if data.get("user_id"):
            from accounts.models import User

            invitee = get_object_or_404(User, pk=data["user_id"])
            email = invitee.email
        if not email:
            return Response({"error": "Provide an email address or a user."}, status=400)

        from accounts.models import User as UserModel

        if invitee is None:
            invitee = UserModel.objects.filter(email=email).first()

        invitation = Invitation.objects.create(
            event=event,
            invited_by=request.user,
            invitee=invitee,
            email=email,
            message=data.get("message", ""),
            expires_at=timezone.now() + timedelta(days=14),
        )
        if invitee:
            notify_user(
                invitee,
                f"You're invited: {event.title}",
                invitation.message or f"{request.user.email} invited you to {event.title}.",
                category=Notification.Category.INVITATION,
                link=f"/invite/{invitation.token}",
                event=event,
            )
        send_invitation_email(invitation)
        return Response({"invitation": InvitationSerializer(invitation).data}, status=201)


class InvitationMineView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        invites = (
            Invitation.objects.filter(Q(invitee=request.user) | Q(email=request.user.email))
            .select_related("event")
            .order_by("-created_at")
        )
        # Lazy expiry.
        now = timezone.now()
        for inv in invites:
            if inv.status == Invitation.Status.PENDING and inv.expires_at and inv.expires_at < now:
                inv.status = Invitation.Status.EXPIRED
                inv.save(update_fields=["status"])
        return Response({"invitations": InvitationSerializer(invites, many=True).data})


class InvitationDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, token):
        invitation = get_object_or_404(Invitation.objects.select_related("event", "invited_by"), token=token)
        if invitation.status == Invitation.Status.PENDING and invitation.expires_at and invitation.expires_at < timezone.now():
            invitation.status = Invitation.Status.EXPIRED
            invitation.save(update_fields=["status"])
        data = InvitationSerializer(invitation).data
        data["event_detail"] = {
            "title": invitation.event.title,
            "starts_at": invitation.event.starts_at,
            "venue": invitation.event.venue,
            "city": invitation.event.city,
            "image_url": invitation.event.image_url,
            "description": invitation.event.description,
        }
        return Response({"invitation": data})


class InvitationRespondView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, token, action):
        invitation = get_object_or_404(Invitation.objects.select_related("event"), token=token)
        if invitation.invitee_id and invitation.invitee_id != request.user.id:
            raise PermissionDenied("This invitation isn't for you.")
        if not invitation.invitee_id and invitation.email.lower() != request.user.email.lower():
            raise PermissionDenied("This invitation isn't for you.")
        if invitation.status != Invitation.Status.PENDING:
            return Response({"error": f"This invitation is already {invitation.status.lower()}."}, status=409)
        if action == "accept":
            invitation.status = Invitation.Status.ACCEPTED
        elif action == "decline":
            invitation.status = Invitation.Status.DECLINED
        else:
            return Response({"error": "Unknown action."}, status=400)
        invitation.invitee = request.user
        invitation.responded_at = timezone.now()
        invitation.save()
        return Response({"invitation": InvitationSerializer(invitation).data})


# ---------------- Support tickets ----------------

class SupportTicketListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if is_admin(request.user):
            tickets = SupportTicket.objects.select_related("user").order_by("-updated_at")
            status = request.query_params.get("status")
            if status:
                tickets = tickets.filter(status=status.upper())
            tickets = tickets[:200]
        else:
            tickets = SupportTicket.objects.filter(user=request.user).order_by("-updated_at")
        return Response({"tickets": SupportTicketSerializer(tickets, many=True).data})

    def post(self, request):
        serializer = SupportTicketCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ticket = SupportTicket.objects.create(user=request.user, **serializer.validated_data)
        notify_user(
            request.user,
            f"Support ticket #{ticket.id} opened",
            f"We've received '{ticket.subject}' and will get back to you.",
            category=Notification.Category.SUPPORT,
            link=f"/support/{ticket.id}",
        )
        return Response({"ticket": SupportTicketSerializer(ticket).data}, status=201)


class SupportTicketDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_ticket(self, request, pk):
        ticket = get_object_or_404(SupportTicket.objects.select_related("user", "assigned_to"), pk=pk)
        if ticket.user_id != request.user.id and not is_admin(request.user):
            raise PermissionDenied("You don't have access to this ticket.")
        return ticket

    def get(self, request, pk):
        ticket = self.get_ticket(request, pk)
        messages = ticket.messages.select_related("sender").order_by("created_at")
        return Response(
            {
                "ticket": SupportTicketSerializer(ticket).data,
                "messages": SupportMessageSerializer(messages, many=True, context={"request": request}).data,
            }
        )

    def post(self, request, pk):
        """Reply, assign ({assignee_id}, admin) or change status ({status})."""
        ticket = self.get_ticket(request, pk)
        if ticket.status == SupportTicket.Status.CLOSED:
            return Response({"error": "This ticket is closed."}, status=409)

        if "status" in request.data or "assignee_id" in request.data:
            if not is_admin(request.user):
                raise PermissionDenied("Only support staff can do that.")
            if "status" in request.data:
                new_status = (request.data.get("status") or "").upper()
                if new_status not in SupportTicket.Status.values:
                    return Response({"error": "Invalid status."}, status=400)
                ticket.status = new_status
            if "assignee_id" in request.data:
                assignee_id = request.data.get("assignee_id")
                if assignee_id:
                    from accounts.models import User

                    ticket.assigned_to = get_object_or_404(User, pk=assignee_id)
                else:
                    ticket.assigned_to = None
            ticket.save()
            send_support_update_email(ticket.user, ticket)
            return Response({"ticket": SupportTicketSerializer(ticket).data})

        body = (request.data.get("body") or "").strip()
        if not body:
            return Response({"error": "Message body is required."}, status=400)
        msg = SupportMessage.objects.create(ticket=ticket, sender=request.user, body=body)
        if is_admin(request.user):
            if ticket.status in (SupportTicket.Status.OPEN, SupportTicket.Status.WAITING_FOR_USER):
                ticket.status = SupportTicket.Status.IN_PROGRESS
        else:
            # A user reply reopens waiting/resolved tickets.
            if ticket.status in (SupportTicket.Status.WAITING_FOR_USER, SupportTicket.Status.RESOLVED):
                ticket.status = SupportTicket.Status.OPEN
        ticket.save()
        other = ticket.user if is_admin(request.user) else None
        if other is None and ticket.assigned_to:
            other = ticket.assigned_to
        send_support_update_email(ticket.user, ticket, reply_body=body)
        if other and other.id != request.user.id:
            notify_user(
                other,
                f"New reply on ticket #{ticket.id}",
                body[:200],
                category=Notification.Category.SUPPORT,
                link=f"/support/{ticket.id}",
            )
        return Response(
            {"message": SupportMessageSerializer(msg, context={"request": request}).data},
            status=201,
        )


# ---------------- Public support info ----------------

class SupportInfoView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(
            {"supportEmail": settings.SUPPORT_EMAIL, "supportPhone": settings.SUPPORT_PHONE}
        )


# ---------------- FAQ ----------------

class FAQListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        faqs = FAQ.objects.filter(is_published=True)
        category = request.query_params.get("category")
        if category:
            faqs = faqs.filter(category__iexact=category)
        search = request.query_params.get("search")
        if search:
            faqs = faqs.filter(Q(question__icontains=search) | Q(answer__icontains=search))
        categories = list(
            FAQ.objects.filter(is_published=True).values_list("category", flat=True).distinct()
        )
        return Response({"faqs": FAQSerializer(faqs, many=True).data, "categories": categories})


# ---------------- Reports ----------------

class ReportListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if is_admin(request.user):
            reports = Report.objects.select_related("user", "event", "booking").order_by("-created_at")[:200]
            status = request.query_params.get("status")
            if status:
                reports = reports.filter(status=status.upper())
        else:
            reports = Report.objects.filter(user=request.user).order_by("-created_at")
        return Response({"reports": ReportSerializer(reports, many=True).data})

    def post(self, request):
        serializer = ReportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if data.get("booking") and data["booking"].user_id != request.user.id:
            return Response({"error": "You can only report your own bookings."}, status=403)
        report = Report.objects.create(user=request.user, **data)
        return Response({"report": ReportSerializer(report).data}, status=201)


class ReportStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not is_admin(request.user):
            raise PermissionDenied("Only support staff can do that.")
        report = get_object_or_404(Report, pk=pk)
        new_status = (request.data.get("status") or "").upper()
        if new_status not in Report.Status.values:
            return Response({"error": "Invalid status."}, status=400)
        report.status = new_status
        report.save(update_fields=["status", "updated_at"])
        return Response({"report": ReportSerializer(report).data})
