"""Real booking flow with temporary seat holds and server-side pricing.

Reserved seating:
  select seats -> POST /api/bookings/ {seat_ids} -> seats HELD for N minutes,
  Booking PENDING_PAYMENT -> pay via Razorpay -> webhook/verify confirms ->
  seats BOOKED, tickets minted. Holds expire automatically (cleanup command).

General admission: quantity-based, same pending -> paid lifecycle.
"""

import logging
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db import models, transaction
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import AuditLog
from comms.emails import send_booking_cancellation_email
from comms.services import notify_user
from events.models import Event, Seat, SeatHold, TicketType

from .models import Booking
from .serializers import BookingCreateSerializer, EventRosterBookingSerializer, MyBookingSerializer

logger = logging.getLogger(__name__)


def _audit(user, action, obj=None, request=None, **meta):
    try:
        AuditLog.objects.create(
            user=user if getattr(user, "is_authenticated", False) else None,
            action=action, object_type=type(obj).__name__ if obj is not None else "",
            object_id=str(getattr(obj, "pk", "")) if obj is not None else "",
            ip_address=(request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
                        or request.META.get("REMOTE_ADDR")) if request else None,
            metadata=meta)
    except Exception:
        logger.exception("audit failed %s", action)


def release_expired_holds() -> int:
    """Release HELD seats whose hold expired; expire linked pending bookings. Returns count."""
    now = timezone.now()
    count = 0
    expired_holds = SeatHold.objects.filter(status=SeatHold.Status.ACTIVE, expires_at__lte=now)[:500]
    for hold in expired_holds:
        with transaction.atomic():
            hold = SeatHold.objects.select_for_update().get(pk=hold.pk)
            if hold.status != SeatHold.Status.ACTIVE or hold.expires_at > timezone.now():
                continue
            hold.status = SeatHold.Status.EXPIRED
            hold.save(update_fields=["status"])
            Seat.objects.filter(hold=hold).update(status=Seat.Status.AVAILABLE, hold=None, held_until=None)
            Booking.objects.filter(hold=hold, status=Booking.Status.PENDING_PAYMENT).update(
                status=Booking.Status.EXPIRED)
            count += 1
    if count:
        logger.info("released %s expired seat holds", count)
    return count


class SeatHoldView(APIView):
    """Explicit hold step: lock seats for SEAT_HOLD_MINUTES. Used by seat-map UI countdown."""

    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["bookings"],
                   description="Hold 1-10 seats for SEAT_HOLD_MINUTES. Row-locked; double-holds return 409.")
    def post(self, request, event_id=None):
        from .serializers import BookingCreateSerializer  # noqa (kept for symmetry)

        event = get_object_or_404(Event, pk=request.data.get("event_id") or event_id)
        if event.status != Event.Status.PUBLISHED:
            return Response({"error": "This event is not available for booking."}, status=404)
        if event.seating_type != Event.SeatingType.RESERVED:
            return Response({"error": "This event uses general admission — no seat holds needed."}, status=400)
        seat_ids = request.data.get("seat_ids") or []
        if not seat_ids or len(seat_ids) > 10:
            return Response({"error": "Select 1–10 seats."}, status=400)
        with transaction.atomic():
            seats = list(Seat.objects.select_for_update().filter(id__in=seat_ids, event=event))
            if len(seats) != len(set(seat_ids)):
                return Response({"error": "Some seats don't belong to this event."}, status=400)
            now = timezone.now()
            for s in seats:
                if s.status == Seat.Status.BOOKED:
                    return Response({"error": f"Seat {s.section} {s.row_label}{s.number} is already booked."}, status=409)
                if s.status == Seat.Status.HELD and s.held_until and s.held_until > now:
                    # Allow the same user to re-hold their own seats.
                    if not (s.hold and s.hold.user_id == request.user.id and s.hold.status == SeatHold.Status.ACTIVE):
                        return Response({"error": f"Seat {s.section} {s.row_label}{s.number} is temporarily held. Try another."}, status=409)
            expires = now + timedelta(minutes=settings.SEAT_HOLD_MINUTES)
            hold = SeatHold.objects.create(user=request.user, event=event, expires_at=expires)
            for s in seats:
                s.status = Seat.Status.HELD
                s.hold = hold
                s.held_until = expires
                s.save(update_fields=["status", "hold", "held_until", "updated_at"])
        _audit(request.user, "seats.held", hold, request, event_id=event.id, seats=len(seat_ids))
        return Response({"hold_id": hold.id, "expires_at": hold.expires_at,
                         "expires_in_seconds": settings.SEAT_HOLD_MINUTES * 60}, status=201)

    def delete(self, request, event_id=None):
        hold_id = request.data.get("hold_id") or request.query_params.get("hold_id")
        hold = get_object_or_404(SeatHold, pk=hold_id, user=request.user, status=SeatHold.Status.ACTIVE)
        with transaction.atomic():
            hold = SeatHold.objects.select_for_update().get(pk=hold.pk)
            hold.status = SeatHold.Status.RELEASED
            hold.save(update_fields=["status"])
            Seat.objects.filter(hold=hold).update(status=Seat.Status.AVAILABLE, hold=None, held_until=None)
        return Response({"ok": True})


class BookingCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["bookings"],
                   description="Create a PENDING_PAYMENT booking with server-side pricing. Reserved seats are HELD; pay via /api/payments/. No card data accepted.")
    def post(self, request):
        from payments.gateway import quote_totals

        release_expired_holds()
        serializer = BookingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        event = get_object_or_404(Event, pk=data["eventId"])
        if event.status != Event.Status.PUBLISHED:
            return Response({"error": "This event is not available for booking."}, status=404)

        now = timezone.now()
        if event.booking_opens_at and now < event.booking_opens_at:
            return Response({"error": f"Booking opens on {event.booking_opens_at:%b %d, %Y at %I:%M %p}."}, status=409)
        if event.booking_closes_at and now > event.booking_closes_at:
            return Response({"error": "Booking for this event has closed."}, status=409)

        ticket_type = get_object_or_404(TicketType, pk=data["ticketTypeId"], event=event)
        if ticket_type.sale_start and now < ticket_type.sale_start:
            return Response({"error": "Sale for this ticket type hasn't started."}, status=409)
        if ticket_type.sale_end and now > ticket_type.sale_end:
            return Response({"error": "Sale for this ticket type has ended."}, status=409)

        seat_ids = data.get("seat_ids") or []
        if event.seating_type == Event.SeatingType.RESERVED:
            if not seat_ids:
                return Response({"error": "Please select your seats."}, status=400)
            quantity = len(seat_ids)
        else:
            if seat_ids:
                return Response({"error": "This event uses general admission — seats can't be selected."}, status=400)
            quantity = data["quantity"]

        already = (Booking.objects.filter(
            user=request.user, ticket_type=ticket_type,
            status__in=[Booking.Status.CONFIRMED, Booking.Status.PENDING_PAYMENT]
        ).aggregate(total=models.Sum("quantity"))["total"] or 0)
        if already + quantity > ticket_type.max_per_user:
            return Response(
                {"error": f"Limit of {ticket_type.max_per_user} ticket(s) per user for {ticket_type.name}."},
                status=409)

        coupon_code = (data.get("coupon_code") or "").strip().upper()

        with transaction.atomic():
            ticket_type = TicketType.objects.select_for_update().get(pk=ticket_type.pk)
            remaining = ticket_type.quantity_total - ticket_type.quantity_sold
            if quantity > remaining:
                return Response({"error": f"Only {remaining} ticket(s) left for {ticket_type.name}."}, status=409)

            seats = []
            hold = None
            if seat_ids:
                seats = list(Seat.objects.select_for_update().filter(id__in=seat_ids, event=event))
                if len(seats) != len(set(seat_ids)):
                    return Response({"error": "Some selected seats don't belong to this event."}, status=400)
                for s in seats:
                    if s.status == Seat.Status.BOOKED:
                        return Response(
                            {"error": f"Seat {s.section} {s.row_label}{s.number} was just booked. Pick another."},
                            status=409)
                    if s.status == Seat.Status.HELD and s.held_until and s.held_until > now:
                        if not (s.hold and s.hold.user_id == request.user.id
                                and s.hold.status == SeatHold.Status.ACTIVE):
                            return Response(
                                {"error": f"Seat {s.section} {s.row_label}{s.number} is temporarily held. Pick another."},
                                status=409)
                # Server-side subtotal from seat prices (never trust client).
                subtotal = sum((s.price for s in seats), start=Decimal("0.00"))
            else:
                subtotal = ticket_type.price * quantity

            try:
                quote = quote_totals(subtotal, coupon=coupon_code or None, user=request.user)
            except ValueError as exc:
                return Response({"error": str(exc)}, status=400)

            expires_at = now + timedelta(minutes=settings.SEAT_HOLD_MINUTES)
            if seats:
                hold = SeatHold.objects.create(
                    user=request.user, event=event, ticket_type=ticket_type, expires_at=expires_at)
                for s in seats:
                    s.status = Seat.Status.HELD
                    s.hold = hold
                    s.held_until = expires_at
                    s.booking = None
                    s.save(update_fields=["status", "hold", "held_until", "booking", "updated_at"])

            # Reserve inventory optimistically; released on expiry/cancel.
            ticket_type.quantity_sold += quantity
            ticket_type.save(update_fields=["quantity_sold"])

            booking = Booking.objects.create(
                user=request.user, event=event, ticket_type=ticket_type, quantity=quantity,
                subtotal=quote["subtotal"], discount=quote["discount"],
                platform_fee=quote["fee"], tax_amount=quote["tax"], total_amount=quote["total"],
                coupon=quote["coupon_obj"], coupon_code=coupon_code if quote["coupon_obj"] else "",
                status=Booking.Status.PENDING_PAYMENT, hold=hold, expires_at=expires_at)
            if seats:
                booking.seats.set(seats)

        _audit(request.user, "booking.created", booking, request, reference=booking.reference,
               total=str(booking.total_amount))
        logger.info("booking created id=%s ref=%s user=%s total=%s", booking.id, booking.reference,
                    request.user.id, booking.total_amount)
        notify_user(request.user, f"Complete your payment: {event.title}",
                    f"Booking {booking.reference} held for {settings.SEAT_HOLD_MINUTES} min — ₹{booking.total_amount} due.",
                    category="BOOKING", link="/my-bookings", event=event, booking=booking)
        return Response({"booking": MyBookingSerializer(booking).data,
                         "expires_in_seconds": settings.SEAT_HOLD_MINUTES * 60}, status=201)


class MyBookingsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        release_expired_holds()
        bookings = (Booking.objects.filter(user=request.user)
                    .select_related("event", "ticket_type")
                    .prefetch_related("seats", "tickets").order_by("-created_at"))
        kind = request.query_params.get("kind")
        now = timezone.now()
        items = list(bookings)
        if kind == "upcoming":
            items = [b for b in items if b.event.starts_at >= now and b.status == Booking.Status.CONFIRMED]
        elif kind == "past":
            items = [b for b in items if not (b.event.starts_at >= now and b.status == Booking.Status.CONFIRMED)]
        return Response({"bookings": MyBookingSerializer(items, many=True).data})


class BookingDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        booking = get_object_or_404(
            Booking.objects.select_related("event", "ticket_type").prefetch_related("seats", "tickets"), pk=pk)
        if booking.user_id != request.user.id and request.user.role != "admin":
            raise PermissionDenied("Not your booking.")
        return Response({"booking": MyBookingSerializer(booking).data})


class BookingCancelView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        booking = get_object_or_404(Booking.objects.select_related("event", "ticket_type"), pk=pk)
        if booking.user_id != request.user.id and request.user.role != "admin":
            raise PermissionDenied("You don't have permission to cancel this booking.")
        if booking.status in (Booking.Status.CANCELLED, Booking.Status.REFUNDED):
            return Response({"error": "This booking is already cancelled."}, status=409)
        if booking.status == Booking.Status.EXPIRED:
            return Response({"error": "This booking hold already expired."}, status=409)

        # Cancellation window: no cancel within N hours of start (unless admin).
        if request.user.role != "admin" and booking.status == Booking.Status.CONFIRMED:
            cutoff = booking.event.starts_at - timedelta(hours=settings.CANCELLATION_WINDOW_HOURS)
            if timezone.now() > cutoff:
                return Response(
                    {"error": f"Cancellation closes {settings.CANCELLATION_WINDOW_HOURS}h before the event."},
                    status=409)

        paid = booking.payments.filter(status="success").exists() if hasattr(booking, "payments") else False
        with transaction.atomic():
            booking = Booking.objects.select_for_update().get(pk=booking.pk)
            ticket_type = TicketType.objects.select_for_update().get(pk=booking.ticket_type_id)
            ticket_type.quantity_sold = max(0, ticket_type.quantity_sold - booking.quantity)
            ticket_type.save(update_fields=["quantity_sold"])
            Seat.objects.filter(booking=booking).update(status=Seat.Status.AVAILABLE, booking=None,
                                                        hold=None, held_until=None)
            Seat.objects.filter(hold=booking.hold).update(status=Seat.Status.AVAILABLE, booking=None,
                                                          hold=None, held_until=None) if booking.hold_id else None
            booking.seats.clear()
            if booking.hold_id:
                SeatHold.objects.filter(pk=booking.hold_id, status=SeatHold.Status.ACTIVE).update(
                    status=SeatHold.Status.RELEASED)
            booking.status = Booking.Status.CANCELLED
            booking.cancelled_at = timezone.now()
            booking.save(update_fields=["status", "cancelled_at"])
            from payments.models import Ticket as _Ticket

            _Ticket.objects.filter(booking=booking, status=_Ticket.Status.VALID).update(
                status=_Ticket.Status.CANCELLED)

        event = booking.event
        send_booking_cancellation_email(booking.user, booking, event)
        notify_user(booking.user, f"Booking cancelled: {event.title}",
                    f"Booking {booking.reference} was cancelled.", category="BOOKING",
                    link="/my-bookings", event=event, booking=booking)
        _audit(request.user, "booking.cancelled", booking, request, reference=booking.reference)

        refund_info = None
        if paid:
            # Paid bookings: raise a gateway refund request automatically.
            from payments.models import Payment, Refund
            from payments.gateway import get_gateway

            payment = Payment.objects.filter(booking=booking, status="success").order_by("-created_at").first()
            if payment and not Refund.objects.filter(payment=payment).exists():
                refund = Refund.objects.create(payment=payment, booking=booking,
                                               amount=payment.amount, reason="booking cancelled")
                client = get_gateway()
                if client is not None:
                    try:
                        gw = client.payment.refund(payment.gateway_payment_id,
                                                   {"amount": int(payment.amount * 100)})
                        refund.gateway_refund_id = gw.get("id", "")
                        refund.status = Refund.Status.PROCESSING
                        refund.raw_response = gw
                        refund.save()
                    except Exception:
                        refund.status = Refund.Status.FAILED
                        refund.raw_response = {"error": "gateway refund call failed"}
                        refund.save()
                        logger.exception("auto refund failed booking %s", booking.id)
                else:
                    refund.status = Refund.Status.PROCESSING
                    refund.raw_response = {"test": True}
                    refund.save(update_fields=["status", "raw_response"])
                refund_info = {"id": refund.id, "status": refund.status, "amount": refund.amount}
        return Response({"booking": MyBookingSerializer(booking).data, "refund": refund_info})


def can_manage_event(user, event):
    return user.role == "admin" or event.organizer_id == user.id


class BookingCheckInView(APIView):
    """Door check-in: mark a confirmed booking as checked in."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        booking = get_object_or_404(Booking.objects.select_related("event"), pk=pk)
        if not can_manage_event(request.user, booking.event):
            raise PermissionDenied("You don't have permission to check in this booking.")
        if booking.status != Booking.Status.CONFIRMED:
            return Response({"error": "Only confirmed bookings can be checked in."}, status=409)
        if booking.checked_in:
            return Response({"error": "This ticket is already checked in."}, status=409)
        booking.checked_in = True
        booking.checked_in_at = timezone.now()
        booking.save(update_fields=["checked_in", "checked_in_at"])
        _audit(request.user, "booking.checkin", booking, request, reference=booking.reference)
        return Response({"booking": EventRosterBookingSerializer(booking).data})


class BookingLookupView(APIView):
    """Find a booking by ticket reference (for scanning/typing at the door)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        reference = (request.query_params.get("reference") or "").strip().upper()
        if not reference:
            return Response({"error": "Provide a ticket reference."}, status=400)
        booking = get_object_or_404(
            Booking.objects.select_related("event", "ticket_type", "user"),
            reference=reference,
        )
        if not can_manage_event(request.user, booking.event):
            raise PermissionDenied("You don't have permission to view this booking.")
        return Response({"booking": EventRosterBookingSerializer(booking).data})
