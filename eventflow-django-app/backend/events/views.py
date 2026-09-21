from django.db.models import Avg, Count, Min, Q, Sum
from django.utils.dateparse import parse_date
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Event, Review, TicketType, Wishlist
from .permissions import IsEventOwnerOrAdmin, IsOrganizerOrAdmin
from .serializers import (
    EventCreateSerializer,
    EventReadSerializer,
    EventUpdateSerializer,
    ReviewSerializer,
    TicketTypeSerializer,
    WishlistSerializer,
)


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

        date_from = parse_date(request.query_params.get("date_from") or "")
        if date_from:
            events = events.filter(starts_at__date__gte=date_from)
        date_to = parse_date(request.query_params.get("date_to") or "")
        if date_to:
            events = events.filter(starts_at__date__lte=date_to)

        if request.query_params.get("featured") == "true":
            events = events.filter(is_featured=True)

        events = events.annotate(
            avg_rating=Avg("reviews__rating"),
            review_count=Count("reviews", distinct=True),
            tickets_sold=Sum("ticket_types__quantity_sold"),
            min_price=Min("ticket_types__price"),
        )

        ordering = request.query_params.get("ordering", "starts_at")
        if ordering == "popular" or request.query_params.get("trending") == "true":
            events = events.order_by("-tickets_sold", "starts_at")
        elif ordering == "rating":
            events = events.order_by("-avg_rating", "starts_at")
        elif ordering == "price_low":
            events = events.order_by("min_price", "starts_at")
        elif ordering == "price_high":
            events = events.order_by("-min_price", "starts_at")
        elif ordering == "-starts_at":
            events = events.order_by("-starts_at")
        else:
            events = events.order_by("starts_at")

        try:
            page = max(1, int(request.query_params.get("page", 1)))
        except ValueError:
            page = 1
        try:
            page_size = min(50, max(1, int(request.query_params.get("page_size", 12))))
        except ValueError:
            page_size = 12

        total = events.count()
        pages = max(1, -(-total // page_size))
        page = min(page, pages)
        start = (page - 1) * page_size
        page_events = list(
            events.select_related("organizer").prefetch_related("ticket_types")[start : start + page_size]
        )
        return Response(
            {
                "events": serialize_events(page_events, request),
                "page": page,
                "pages": pages,
                "total": total,
            }
        )

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
        event = get_object_or_404(
            Event.objects.select_related("organizer")
            .prefetch_related("ticket_types")
            .annotate(
                avg_rating=Avg("reviews__rating"),
                review_count=Count("reviews", distinct=True),
                tickets_sold=Sum("ticket_types__quantity_sold"),
            ),
            pk=pk,
        )
        data = EventReadSerializer(
            event,
            context={"request": request, "wishlist_ids": wishlist_ids_for(request.user)},
        ).data
        return Response({"event": data})

    def put(self, request, pk):
        event = self.get_object(pk)
        before = {
            "starts_at": event.starts_at,
            "ends_at": event.ends_at,
            "venue": event.venue,
            "city": event.city,
            "status": event.status,
        }
        serializer = EventUpdateSerializer(event, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        event.refresh_from_db()
        changes = []
        if event.starts_at != before["starts_at"]:
            changes.append(f"Start time changed to {event.starts_at:%a, %b %d %Y at %I:%M %p}.")
        if event.ends_at != before["ends_at"]:
            changes.append(f"End time changed to {event.ends_at:%a, %b %d %Y at %I:%M %p}.")
        if event.venue != before["venue"]:
            changes.append(f"Venue changed from {before['venue']} to {event.venue}.")
        if event.city != before["city"]:
            changes.append(f"City changed from {before['city']} to {event.city}.")
        if event.status != before["status"]:
            if event.status == Event.Status.CANCELLED:
                changes.append("This event has been cancelled.")
            elif event.status == Event.Status.PUBLISHED and before["status"] == Event.Status.CANCELLED:
                changes.append("This event is back on — cancellation lifted.")
            else:
                changes.append(f"Event status changed to {event.status}.")
        notified = 0
        if changes:
            from comms.services import notify_event_change

            notified = notify_event_change(event, changes)
        data = EventReadSerializer(event).data
        return Response({"event": data, "notified": notified})

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


def wishlist_ids_for(user):
    if not user.is_authenticated:
        return set()
    return set(Wishlist.objects.filter(user=user).values_list("event_id", flat=True))


def serialize_events(events, request):
    return EventReadSerializer(
        events, many=True, context={"request": request, "wishlist_ids": wishlist_ids_for(request.user)}
    ).data


class WishlistView(APIView):
    """The signed-in user's saved events."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        items = Wishlist.objects.filter(user=request.user).select_related("event").prefetch_related("event__ticket_types")
        return Response(
            {"wishlist": WishlistSerializer(items, many=True, context={"request": request}).data}
        )


class EventWishlistView(APIView):
    """Save / unsave a single event."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        event = get_object_or_404(Event, pk=pk)
        Wishlist.objects.get_or_create(user=request.user, event=event)
        return Response({"wishlisted": True}, status=201)

    def delete(self, request, pk):
        event = get_object_or_404(Event, pk=pk)
        Wishlist.objects.filter(user=request.user, event=event).delete()
        return Response({"wishlisted": False})


class EventReviewsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        event = get_object_or_404(Event, pk=pk)
        reviews = event.reviews.select_related("user").order_by("-created_at")
        return Response(
            {"reviews": ReviewSerializer(reviews, many=True, context={"request": request}).data}
        )

    def post(self, request, pk):
        if not request.user.is_authenticated:
            return Response({"error": "Sign in to leave a review."}, status=401)
        event = get_object_or_404(Event, pk=pk)
        serializer = ReviewSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        # One review per user per event: posting again updates the existing one.
        review, created = Review.objects.update_or_create(
            user=request.user,
            event=event,
            defaults={
                "rating": serializer.validated_data["rating"],
                "comment": serializer.validated_data.get("comment", ""),
            },
        )
        return Response(
            {"review": ReviewSerializer(review, context={"request": request}).data},
            status=201 if created else 200,
        )


class ReviewDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        review = get_object_or_404(Review, pk=pk)
        if review.user_id != request.user.id and request.user.role != "admin":
            raise PermissionDenied("You don't have permission to delete this review.")
        review.delete()
        return Response({"ok": True})
