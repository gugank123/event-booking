from decimal import Decimal

from django.db import transaction
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from events.models import Event, TicketType

from .models import Booking
from .serializers import CheckoutSerializer, MyBookingSerializer


class BookingCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        event = get_object_or_404(Event, pk=data["eventId"])
        if event.status != Event.Status.PUBLISHED:
            return Response({"error": "This event is not available for booking."}, status=404)

        ticket_type = get_object_or_404(TicketType, pk=data["ticketTypeId"], event=event)

        with transaction.atomic():
            ticket_type.refresh_from_db()
            remaining = ticket_type.quantity_total - ticket_type.quantity_sold
            if data["quantity"] > remaining:
                return Response(
                    {"error": f"Only {remaining} ticket(s) left for {ticket_type.name}."}, status=409
                )

            # "Charge" the mock payment method -- always succeeds once validation passes.
            total_amount = (ticket_type.price * data["quantity"]).quantize(Decimal("0.01"))

            ticket_type.quantity_sold += data["quantity"]
            ticket_type.save()

            booking = Booking.objects.create(
                user=request.user,
                event=event,
                ticket_type=ticket_type,
                quantity=data["quantity"],
                total_amount=total_amount,
                card_last4=data["cardNumber"][-4:],
            )

        return Response(
            {
                "booking": {
                    "id": booking.id,
                    "reference": booking.reference,
                    "quantity": booking.quantity,
                    "totalAmount": booking.total_amount,
                    "cardLast4": booking.card_last4,
                    "status": booking.status,
                }
            },
            status=201,
        )


class MyBookingsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        bookings = (
            Booking.objects.filter(user=request.user)
            .select_related("event", "ticket_type")
            .order_by("-created_at")
        )
        return Response({"bookings": MyBookingSerializer(bookings, many=True).data})


class BookingCancelView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        booking = get_object_or_404(Booking, pk=pk)
        if booking.user_id != request.user.id and request.user.role != "admin":
            raise PermissionDenied("You don't have permission to cancel this booking.")
        if booking.status == Booking.Status.CANCELLED:
            return Response({"error": "This booking is already cancelled."}, status=409)

        with transaction.atomic():
            ticket_type = booking.ticket_type
            ticket_type.quantity_sold = max(0, ticket_type.quantity_sold - booking.quantity)
            ticket_type.save()
            booking.status = Booking.Status.CANCELLED
            from django.utils import timezone

            booking.cancelled_at = timezone.now()
            booking.save()

        return Response({"booking": MyBookingSerializer(booking).data})
