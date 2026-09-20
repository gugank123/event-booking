from decimal import Decimal

from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from accounts.serializers import UserSerializer
from bookings.models import Booking
from events.models import Event
from events.permissions import IsAdmin


class AdminStatsView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        users = User.objects.all()
        events = Event.objects.all()
        confirmed = Booking.objects.filter(status=Booking.Status.CONFIRMED)
        revenue = sum((b.total_amount for b in confirmed), start=Decimal("0"))
        tickets_sold = sum((b.quantity for b in confirmed), start=0)

        return Response(
            {
                "totalUsers": users.count(),
                "attendees": users.filter(role="attendee").count(),
                "organizers": users.filter(role="organizer").count(),
                "admins": users.filter(role="admin").count(),
                "totalEvents": events.count(),
                "publishedEvents": events.filter(status="published").count(),
                "cancelledEvents": events.filter(status="cancelled").count(),
                "totalBookings": confirmed.count(),
                "ticketsSold": tickets_sold,
                "revenue": revenue,
            }
        )


class AdminUsersView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        return Response({"users": UserSerializer(User.objects.all().order_by("-date_joined"), many=True).data})


class AdminUserUpdateView(APIView):
    permission_classes = [IsAdmin]

    def patch(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        role = request.data.get("role")
        status_val = request.data.get("status")

        if user.id == request.user.id and (status_val == "suspended" or role):
            return Response({"error": "You can't change your own role or suspend yourself."}, status=400)

        if role in ("attendee", "organizer", "admin"):
            user.role = role
        if status_val in ("active", "suspended"):
            user.is_active = status_val == "active"
        user.save()
        return Response({"user": UserSerializer(user).data})


class AdminEventsView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        events = Event.objects.select_related("organizer").order_by("-created_at")
        data = []
        for e in events:
            confirmed = e.bookings.filter(status=Booking.Status.CONFIRMED)
            data.append(
                {
                    "id": e.id,
                    "title": e.title,
                    "status": e.status,
                    "startsAt": e.starts_at,
                    "organizerName": (e.organizer.get_full_name() or e.organizer.email).strip(),
                    "ticketsSold": sum((b.quantity for b in confirmed), start=0),
                    "revenue": sum((b.total_amount for b in confirmed), start=Decimal("0")),
                }
            )
        return Response({"events": data})
