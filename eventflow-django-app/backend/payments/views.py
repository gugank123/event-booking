"""Real Razorpay payment flow.

Frontend -> POST /api/payments/create-order/ {booking_id}
  -> backend creates Razorpay order + Payment row (CREATED/PENDING)
  -> frontend opens Razorpay Checkout with key_id + order_id
  -> customer pays on Razorpay (we never see card/UPI data)
  -> EITHER frontend POST /api/payments/verify/ {order_id, payment_id, signature}
     OR Razorpay POST /api/payments/webhook/ (signature-verified)
  -> backend verifies signature server-side, then in one DB transaction:
     booking -> CONFIRMED, seats -> BOOKED, tickets generated, emails sent.
     Processing is idempotent: repeated verify/webhook calls are safe.
"""

import json
import logging
from decimal import Decimal

from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import extend_schema
from rest_framework import serializers as drf_serializers
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import AuditLog
from bookings.models import Booking
from comms.emails import send_booking_confirmation_email, send_payment_confirmation_email
from comms.services import notify_user
from events.models import Seat, SeatHold
from events.permissions import IsAdmin

from .gateway import (
    create_gateway_order,
    verify_payment_signature,
    verify_webhook_signature,
)
from .models import Coupon, CouponRedemption, Payment, Refund, Ticket
from .serializers import CouponSerializer, PaymentSerializer, RefundSerializer, TicketSerializer

logger = logging.getLogger(__name__)


def _audit(user, action, obj=None, request=None, **meta):
    try:
        AuditLog.objects.create(
            user=user if getattr(user, "is_authenticated", False) else None,
            action=action,
            object_type=type(obj).__name__ if obj is not None else "",
            object_id=str(getattr(obj, "pk", "")) if obj is not None else "",
            ip_address=_ip(request) if request else None,
            metadata={k: v for k, v in meta.items() if k not in ("password", "secret", "signature", "card")},
        )
    except Exception:
        logger.exception("audit log failed for %s", action)


def _ip(request):
    if not request:
        return None
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _confirm_booking(payment: Payment, gateway_payment_id: str, event_id: str = "") -> bool:
    """Idempotent confirm: returns True if this call performed the confirm."""
    from django.conf import settings as _s

    with transaction.atomic():
        payment = Payment.objects.select_for_update().get(pk=payment.pk)
        if payment.status == Payment.Status.SUCCESS:
            return False  # already handled (duplicate webhook/verify)
        booking = Booking.objects.select_for_update().get(pk=payment.booking_id)
        if booking.status == Booking.Status.CONFIRMED:
            payment.status = Payment.Status.SUCCESS
            if gateway_payment_id:
                payment.gateway_payment_id = gateway_payment_id
            if event_id and event_id not in (payment.processed_events or []):
                payment.processed_events = (payment.processed_events or []) + [event_id]
            payment.save()
            return False

        payment.status = Payment.Status.SUCCESS
        if gateway_payment_id:
            payment.gateway_payment_id = gateway_payment_id
        if event_id and event_id not in (payment.processed_events or []):
            payment.processed_events = (payment.processed_events or []) + [event_id]
        payment.save()

        booking.status = Booking.Status.CONFIRMED
        booking.save(update_fields=["status"])

        # Permanently book held seats.
        if booking.hold_id:
            hold = SeatHold.objects.filter(pk=booking.hold_id).first()
            if hold and hold.status == SeatHold.Status.ACTIVE:
                hold.status = SeatHold.Status.CONVERTED
                hold.booking = booking
                hold.save(update_fields=["status", "booking"])
        seats = list(Seat.objects.select_for_update().filter(bookings=booking)) if booking.pk else []
        # Seats may be linked via M2M (general flow links at creation). Mark all BOOKED.
        for seat in Seat.objects.select_for_update().filter(bookings=booking):
            seat.status = Seat.Status.BOOKED
            seat.booking = booking
            seat.hold = None
            seat.held_until = None
            seat.save(update_fields=["status", "booking", "hold", "held_until", "updated_at"])
        # Any other seats still HELD under this booking's hold -> book them too.
        if booking.hold_id:
            for seat in Seat.objects.select_for_update().filter(hold_id=booking.hold_id):
                seat.status = Seat.Status.BOOKED
                seat.booking = booking
                seat.hold = None
                seat.held_until = None
                seat.save(update_fields=["status", "booking", "hold", "held_until", "updated_at"])
                booking.seats.add(seat)

        # Coupon redemption (once).
        if booking.coupon_id and booking.user_id:
            CouponRedemption.objects.get_or_create(
                coupon_id=booking.coupon_id, user_id=booking.user_id, booking=booking,
                defaults={"discount_amount": booking.discount},
            )
            Coupon.objects.filter(pk=booking.coupon_id).update(times_used=F("times_used") + 1)

        # Generate tickets (once): one per seat, or `quantity` GA tickets.
        if not booking.tickets.exists():
            linked = list(booking.seats.all())
            if linked:
                for seat in linked:
                    Ticket.objects.create(booking=booking, event=booking.event,
                                          user=booking.user, seat=seat)
            else:
                for _ in range(booking.quantity):
                    Ticket.objects.create(booking=booking, event=booking.event, user=booking.user)

    # Outside the transaction: mail + notify (failures never roll back payment).
    try:
        send_booking_confirmation_email(booking.user, booking, booking.event, booking.ticket_type)
        send_payment_confirmation_email(booking.user, payment, booking)
    except Exception:
        logger.exception("post-payment email failed for booking %s", booking.id)
    notify_user(booking.user, f"Payment successful: {booking.event.title}",
                f"Booking {booking.reference} confirmed — ₹{booking.total_amount}.",
                category="PAYMENT", link="/my-bookings", event=booking.event, booking=booking)
    _audit(booking.user, "payment.success", payment, booking_id=booking.id, reference=booking.reference)
    logger.info("booking confirmed: id=%s ref=%s order=%s", booking.id, booking.reference,
                payment.gateway_order_id)
    return True


class PaymentOrderView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["payments"],
                   description="Create a Razorpay order for a PENDING booking. Returns order_id + public key_id for Checkout.",
                   request=drf_serializers.Serializer)
    def post(self, request):
        booking = get_object_or_404(Booking, pk=request.data.get("booking_id"), user=request.user)
        if booking.status == Booking.Status.CONFIRMED:
            return Response({"error": "This booking is already confirmed."}, status=409)
        if booking.status in (Booking.Status.CANCELLED, Booking.Status.REFUNDED, Booking.Status.EXPIRED):
            return Response({"error": "This booking can no longer be paid for."}, status=409)
        # Reuse a live order for the same booking to avoid duplicates.
        existing = Payment.objects.filter(
            booking=booking, status__in=[Payment.Status.CREATED, Payment.Status.PENDING]
        ).order_by("-created_at").first()
        if existing:
            from django.conf import settings as _s

            return Response({"order_id": existing.gateway_order_id, "amount": existing.amount,
                             "currency": existing.currency, "key_id": _s.RAZORPAY_KEY_ID,
                             "booking_id": booking.id, "reference": booking.reference})
        order = create_gateway_order(
            booking.total_amount, receipt=f"bk{booking.id}-{booking.reference}",
            notes={"booking_id": str(booking.id), "email": request.user.email})
        payment = Payment.objects.create(
            booking=booking, gateway="razorpay", gateway_order_id=order["id"],
            amount=booking.total_amount, currency=order.get("currency", "INR"),
            status=Payment.Status.PENDING)
        booking.status = Booking.Status.PENDING_PAYMENT
        booking.save(update_fields=["status"])
        from django.conf import settings as _s

        _audit(request.user, "payment.order_created", payment, request,
               booking_id=booking.id, order_id=order["id"])
        logger.info("payment order created: booking=%s order=%s amount=%s", booking.id, order["id"], booking.total_amount)
        return Response({"order_id": order["id"], "amount": booking.total_amount,
                         "currency": order.get("currency", "INR"), "key_id": _s.RAZORPAY_KEY_ID,
                         "booking_id": booking.id, "reference": booking.reference}, status=201)


class PaymentVerifyView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["payments"],
                   description="Verify Razorpay checkout signature server-side; confirms booking + mints tickets (idempotent).")
    def post(self, request):
        order_id = (request.data.get("razorpay_order_id") or request.data.get("order_id") or "").strip()
        payment_id = (request.data.get("razorpay_payment_id") or request.data.get("payment_id") or "").strip()
        signature = (request.data.get("razorpay_signature") or request.data.get("signature") or "").strip()
        if not (order_id and payment_id and signature):
            return Response({"error": "Missing payment verification fields."}, status=400)
        payment = get_object_or_404(Payment, gateway_order_id=order_id)
        if payment.booking.user_id != request.user.id and request.user.role != "admin":
            return Response({"error": "Not your payment."}, status=403)
        if not verify_payment_signature(order_id, payment_id, signature):
            payment.status = Payment.Status.FAILED
            payment.gateway_payment_id = payment_id
            payment.save(update_fields=["status", "gateway_payment_id"])
            _audit(request.user, "payment.verify_failed", payment, request, order_id=order_id)
            return Response({"error": "Payment signature verification failed."}, status=400)
        payment.gateway_signature = signature
        payment.save(update_fields=["gateway_signature"])
        _confirm_booking(payment, payment_id)
        booking = payment.booking
        booking.refresh_from_db()
        return Response({"status": booking.status, "reference": booking.reference,
                         "booking_id": booking.id,
                         "tickets": TicketSerializer(booking.tickets.all(), many=True).data})


class PaymentDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        payment = get_object_or_404(Payment.objects.select_related("booking"), pk=pk)
        if payment.booking.user_id != request.user.id and request.user.role not in ("admin", "organizer"):
            return Response({"error": "Not your payment."}, status=403)
        return Response({"payment": PaymentSerializer(payment).data})


class RazorpayWebhookView(APIView):
    """POST /api/payments/webhook/ — Razorpay server-to-server callback.

    Verifies HMAC signature, dedupes by event id, confirms booking exactly once.
    CSRF-exempt + AllowAny by necessity (called by Razorpay, not the browser).
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    @extend_schema(tags=["payments"], auth=[],
                   description="Razorpay webhook. Verifies HMAC signature, dedupes by event id, confirms booking exactly once. Source of truth alongside /verify/.")
    def post(self, request):
        from django.conf import settings as _s

        raw = request.body or b""
        signature = request.META.get("HTTP_X_RAZORPAY_SIGNATURE", "")
        if _s.PAYMENT_WEBHOOK_ALLOWED_IPS:
            ip = (request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
                  or request.META.get("REMOTE_ADDR", ""))
            if ip and ip not in _s.PAYMENT_WEBHOOK_ALLOWED_IPS:
                logger.warning("webhook from untrusted ip %s", ip)
                return Response({"error": "Forbidden."}, status=403)
        if not verify_webhook_signature(raw, signature):
            logger.warning("webhook signature mismatch")
            return Response({"error": "Bad signature."}, status=400)
        try:
            payload = json.loads(raw.decode() or "{}")
        except ValueError:
            return Response({"error": "Bad payload."}, status=400)
        event = payload.get("event", "")
        event_id = payload.get("id", "") or payload.get("event_id", "")
        logger.info("webhook received: event=%s id=%s", event, event_id)
        entity = ((payload.get("payload") or {}).get("payment") or {}).get("entity") or {}
        order_id = entity.get("order_id", "")
        payment_id = entity.get("id", "")
        if not order_id:
            return Response({"ok": True})  # nothing to do, but acknowledge
        try:
            payment = Payment.objects.select_related("booking").get(gateway_order_id=order_id)
        except Payment.DoesNotExist:
            logger.warning("webhook for unknown order %s", order_id)
            return Response({"ok": True})
        if event_id and event_id in (payment.processed_events or []):
            return Response({"ok": True, "duplicate": True})  # idempotent replay
        if event == "payment.captured" or entity.get("status") == "captured":
            _confirm_booking(payment, payment_id, event_id=event_id)
        elif event in ("payment.failed",) or entity.get("status") == "failed":
            with transaction.atomic():
                p = Payment.objects.select_for_update().get(pk=payment.pk)
                if p.status != Payment.Status.SUCCESS:
                    p.status = Payment.Status.FAILED
                    if payment_id:
                        p.gateway_payment_id = payment_id
                    p.raw_response = entity
                    p.save()
            booking = payment.booking
            notify_user(booking.user, f"Payment failed: {booking.event.title}",
                        f"Payment for booking {booking.reference} failed. Your seats are still held briefly.",
                        category="PAYMENT", link="/my-bookings", event=booking.event, booking=booking)
        else:
            payment.raw_response = entity
            payment.save(update_fields=["raw_response"])
        return Response({"ok": True})


# ---------------- Coupons ----------------

class CouponValidateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from payments.gateway import quote_totals

        code = (request.data.get("code") or "").strip().upper()
        try:
            subtotal = Decimal(str(request.data.get("subtotal", "0")))
        except Exception:
            return Response({"error": "Invalid subtotal."}, status=400)
        if not code:
            return Response({"error": "Provide a coupon code."}, status=400)
        try:
            q = quote_totals(subtotal, coupon=code, user=request.user)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=400)
        return Response({"code": code, "discount": str(q["discount"]), "total": str(q["total"])})


class CouponListView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        return Response({"coupons": CouponSerializer(Coupon.objects.all().order_by("code"), many=True).data})

    def post(self, request):
        s = CouponSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        coupon = s.save()
        _audit(request.user, "coupon.created", coupon, request, code=coupon.code)
        return Response({"coupon": CouponSerializer(coupon).data}, status=201)


class CouponDetailView(APIView):
    permission_classes = [IsAdmin]

    def patch(self, request, pk):
        coupon = get_object_or_404(Coupon, pk=pk)
        s = CouponSerializer(coupon, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        _audit(request.user, "coupon.updated", coupon, request, code=coupon.code)
        return Response({"coupon": s.data})

    def delete(self, request, pk):
        coupon = get_object_or_404(Coupon, pk=pk)
        _audit(request.user, "coupon.deleted", coupon, request, code=coupon.code)
        coupon.delete()
        return Response({"ok": True})


# ---------------- Tickets ----------------

class MyTicketsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tickets = Ticket.objects.filter(user=request.user).select_related("event", "booking", "seat")
        return Response({"tickets": TicketSerializer(tickets, many=True).data})


class TicketDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        ticket = get_object_or_404(Ticket.objects.select_related("event", "booking", "seat"), pk=pk)
        if ticket.user_id != request.user.id and request.user.role not in ("admin", "organizer"):
            return Response({"error": "Not your ticket."}, status=403)
        if request.user.role == "organizer" and request.user.id != ticket.event.organizer_id \
                and request.user.role != "admin":
            return Response({"error": "Not your event."}, status=403)
        return Response({"ticket": TicketSerializer(ticket).data})


class TicketVerifyView(APIView):
    """Scan at the door: {qr_token} -> VALID ticket becomes USED exactly once."""

    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["tickets"],
                   description="Verify/scan a ticket by id or qr_token. Single-use: second scan returns 409.")
    def post(self, request, pk=None):
        from bookings.views import can_manage_event

        qr_token = (request.data.get("qr_token") or "").strip()
        ticket = None
        if pk:
            ticket = get_object_or_404(Ticket.objects.select_related("event", "booking"), pk=pk)
        elif qr_token:
            ticket = get_object_or_404(Ticket.objects.select_related("event", "booking"), qr_token=qr_token)
        else:
            return Response({"error": "Provide a ticket id or qr_token."}, status=400)
        if not can_manage_event(request.user, ticket.event):
            return Response({"error": "You can't verify tickets for this event."}, status=403)
        with transaction.atomic():
            ticket = Ticket.objects.select_for_update().get(pk=ticket.pk)
            if ticket.status != Ticket.Status.VALID:
                return Response({"error": f"Ticket is {ticket.status} — cannot be reused.",
                                 "ticket": TicketSerializer(ticket).data}, status=409)
            ticket.status = Ticket.Status.USED
            ticket.used_at = timezone.now()
            ticket.save(update_fields=["status", "used_at"])
        _audit(request.user, "ticket.verified", ticket, request, ticket_number=ticket.ticket_number)
        return Response({"ok": True, "ticket": TicketSerializer(ticket).data})


# ---------------- Refunds ----------------

class RefundRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, booking_id):
        from payments.gateway import get_gateway

        booking = get_object_or_404(Booking.objects.select_related("event"), pk=booking_id)
        if booking.user_id != request.user.id and request.user.role != "admin":
            return Response({"error": "Not your booking."}, status=403)
        payment = Payment.objects.filter(booking=booking, status=Payment.Status.SUCCESS).order_by("-created_at").first()
        if not payment:
            return Response({"error": "No successful payment to refund for this booking."}, status=400)
        if Refund.objects.filter(payment=payment, status__in=["requested", "processing", "completed"]).exists():
            return Response({"error": "A refund is already in progress for this payment."}, status=409)
        refund = Refund.objects.create(payment=payment, booking=booking, amount=payment.amount,
                                       reason=(request.data.get("reason") or "")[:255])
        client = get_gateway()
        if client is None:
            refund.status = Refund.Status.PROCESSING
            refund.raw_response = {"test": True}
            refund.save(update_fields=["status", "raw_response"])
            return Response({"refund": RefundSerializer(refund).data,
                             "detail": "Test mode: refund recorded as processing."}, status=201)
        try:
            gw = client.payment.refund(payment.gateway_payment_id, {"amount": int(payment.amount * 100)})
            refund.gateway_refund_id = gw.get("id", "")
            refund.status = Refund.Status.PROCESSING
            refund.raw_response = gw
            refund.save()
        except Exception as exc:
            refund.status = Refund.Status.FAILED
            refund.raw_response = {"error": str(exc)[:500]}
            refund.save()
            logger.exception("razorpay refund failed for payment %s", payment.id)
            return Response({"error": "Refund request failed at the gateway. Try again later."}, status=502)
        _audit(request.user, "refund.requested", refund, request, booking_id=booking.id)
        return Response({"refund": RefundSerializer(refund).data}, status=201)


class RefundStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        refund = get_object_or_404(Refund.objects.select_related("booking"), pk=pk)
        if refund.booking.user_id != request.user.id and request.user.role != "admin":
            return Response({"error": "Not your refund."}, status=403)
        # Opportunistic status sync for processing refunds (best-effort).
        if refund.status == Refund.Status.PROCESSING and refund.gateway_refund_id:
            from payments.gateway import get_gateway

            client = get_gateway()
            if client is not None:
                try:
                    # Razorpay has no direct refund-fetch; list refunds for payment.
                    refunds = client.payment.fetch_all_refunds(refund.payment.gateway_payment_id) or {}
                    for item in (refunds.get("items") or refunds.get("refunds") or []):
                        if item.get("id") == refund.gateway_refund_id:
                            rstatus = (item.get("status") or "").lower()
                            if rstatus in ("processed", "succeeded", "success"):
                                refund.status = Refund.Status.COMPLETED
                            elif rstatus in ("failed",):
                                refund.status = Refund.Status.FAILED
                            refund.raw_response = item
                            refund.save()
                            if refund.status == Refund.Status.COMPLETED:
                                _settle_refund(refund)
                            break
                except Exception:
                    logger.exception("refund status sync failed %s", refund.id)
        return Response({"refund": RefundSerializer(refund).data})


def _settle_refund(refund: Refund):
    """Mark booking refunded + release inventory. Called only on gateway-confirmed refund."""
    from comms.emails import send_refund_confirmation_email

    with transaction.atomic():
        booking = Booking.objects.select_for_update().get(pk=refund.booking_id)
        payment = Payment.objects.select_for_update().get(pk=refund.payment_id)
        booking.status = Booking.Status.REFUNDED
        booking.cancelled_at = booking.cancelled_at or timezone.now()
        booking.save(update_fields=["status", "cancelled_at"])
        payment.status = Payment.Status.REFUNDED
        payment.save(update_fields=["status"])
        Ticket.objects.filter(booking=booking, status=Ticket.Status.VALID).update(status=Ticket.Status.REFUNDED)
        Seat.objects.filter(booking=booking).update(status=Seat.Status.AVAILABLE, booking=None, hold=None,
                                                    held_until=None)
        booking.seats.clear()
    try:
        send_refund_confirmation_email(booking.user, booking, refund)
    except Exception:
        logger.exception("refund email failed booking %s", booking.id)
    notify_user(booking.user, f"Refund completed: {booking.event.title}",
                f"₹{refund.amount} refunded for booking {booking.reference}.",
                category="PAYMENT", link="/my-bookings", event=booking.event, booking=booking)
    _audit(None, "refund.completed", refund, booking_id=booking.id)
