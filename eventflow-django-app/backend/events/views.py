from django.db.models import Q
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Event, TicketType
from .permissions import IsEventOwnerOrAdmin, IsOrganizerOrAdmin
from .serializers import EventCreateSerializer, EventReadSerializer, EventUpdateSerializer, TicketTypeSerializer


class EventListCreateView(APIView):
    permission_classes = [IsOrganizerOrAdmin]

    def get(self, request):
        mine = request.query_params.get("mine") == "true"
        if mine:
            if not request.user.is_authenticated:
                return Response({"error": "Sign in to see your events."}, status=401)
            events = Event.objects.filter(organizer=request.user)
        else:
            events = Event.objects.filter(status=Event.Status.PUBLISHED)

        category = request.query_params.get("category")
        if category:
            events = events.filter(category__iexact=category)

        search = request.query_params.get("search")
        if search:
            events = events.filter(
                Q(title__icontains=search) | Q(venue__icontains=search) | Q(city__icontains=search)
            )

        events = events.select_related("organizer").prefetch_related("ticket_types")
        return Response({"events": EventReadSerializer(events, many=True).data})

    def post(self, request):
        serializer = EventCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        event = serializer.save()
        return Response({"event": EventReadSerializer(event).data}, status=201)


class EventCategoriesView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        categories = list(
            Event.objects.filter(status=Event.Status.PUBLISHED).values_list("category", flat=True).distinct()
        )
        return Response({"categories": categories})


class EventDetailView(APIView):
    permission_classes = [IsEventOwnerOrAdmin]

    def get_object(self, pk):
        event = get_object_or_404(Event.objects.select_related("organizer").prefetch_related("ticket_types"), pk=pk)
        self.check_object_permissions(self.request, event)
        return event

    def get(self, request, pk):
        event = get_object_or_404(Event.objects.select_related("organizer").prefetch_related("ticket_types"), pk=pk)
        return Response({"event": EventReadSerializer(event).data})

    def put(self, request, pk):
        event = self.get_object(pk)
        serializer = EventUpdateSerializer(event, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"event": EventReadSerializer(event).data})

    def delete(self, request, pk):
        event = self.get_object(pk)
        if event.bookings.filter(status="confirmed").exists():
            return Response(
                {"error": "This event has confirmed bookings. Cancel it instead of deleting."}, status=409
            )
        event.delete()
        return Response({"ok": True})


class TicketTypeCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        event = get_object_or_404(Event, pk=pk)
        if not (request.user.role == "admin" or event.organizer_id == request.user.id):
            raise PermissionDenied("You don't have permission to edit this event.")
        serializer = TicketTypeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ticket_type = serializer.save(event=event)
        return Response({"ticketType": TicketTypeSerializer(ticket_type).data}, status=201)


class EventBookingsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        # Imported here to avoid a module-level circular import between the
        # events and bookings apps.
        from bookings.serializers import EventRosterBookingSerializer

        event = get_object_or_404(Event, pk=pk)
        if not (request.user.role == "admin" or event.organizer_id == request.user.id):
            raise PermissionDenied("You don't have permission to view this.")

        bookings = event.bookings.select_related("user", "ticket_type").order_by("-created_at")
        confirmed = bookings.filter(status="confirmed")
        revenue = sum((b.total_amount for b in confirmed), start=0)
        tickets_sold = sum((b.quantity for b in confirmed), start=0)

        return Response(
            {
                "bookings": EventRosterBookingSerializer(bookings, many=True).data,
                "revenue": revenue,
                "ticketsSold": tickets_sold,
            }
        )
