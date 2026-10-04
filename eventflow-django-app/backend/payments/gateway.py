"""Backend pricing + Razorpay gateway helpers.

All money math happens here, server-side. The frontend never decides prices.
"""

import hashlib
import hmac
import logging
from decimal import Decimal

from django.conf import settings

logger = logging.getLogger(__name__)


def money(value) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"))


def quote_totals(subtotal, coupon=None, user=None) -> dict:
    """Compute discount / fee / tax / total for a subtotal. Validates coupon."""
    from payments.models import Coupon

    subtotal = money(subtotal)
    discount = Decimal("0.00")
    coupon_obj = None
    if coupon:
        code = coupon.strip().upper()
        try:
            coupon_obj = Coupon.objects.get(code=code)
        except Coupon.DoesNotExist:
            raise ValueError("Invalid coupon code.")
        err = coupon_obj.validate_for(user, subtotal)
        if err:
            raise ValueError(err)
        discount = coupon_obj.discount_for(subtotal)
    fee = money(subtotal * Decimal(str(settings.PLATFORM_FEE_PERCENT)) / Decimal("100"))
    tax = money((subtotal - discount) * Decimal(str(settings.TAX_PERCENT)) / Decimal("100"))
    total = money(subtotal - discount + fee + tax)
    return {"subtotal": subtotal, "discount": discount, "fee": fee, "tax": tax, "total": total,
            "coupon_obj": coupon_obj}


def get_gateway():
    """Return configured Razorpay client, or None if keys missing (dev fallback)."""
    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        return None
    import razorpay

    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


def create_gateway_order(amount_rupees: Decimal, receipt: str, notes: dict | None = None) -> dict:
    """Create a Razorpay order. Returns {'id', 'amount', 'currency'}.

    In local dev without keys, returns a clearly-marked test order so the UI
    flow can still be exercised — production (keys set) always hits Razorpay.
    """
    amount_paise = int(money(amount_rupees) * 100)
    client = get_gateway()
    if client is None:
        logger.warning("Razorpay keys missing — issuing local TEST order for %s", receipt)
        fake_id = "order_TEST_" + hashlib.sha256(receipt.encode()).hexdigest()[:14]
        return {"id": fake_id, "amount": amount_paise, "currency": "INR", "test": True}
    order = client.order.create({
        "amount": amount_paise,
        "currency": "INR",
        "receipt": receipt[:40],
        "notes": notes or {},
    })
    return {"id": order["id"], "amount": order["amount"], "currency": order.get("currency", "INR")}


def verify_payment_signature(order_id: str, payment_id: str, signature: str) -> bool:
    """Verify Razorpay checkout signature (HMAC-SHA256 of order|payment)."""
    if not settings.RAZORPAY_KEY_SECRET:
        # No secret configured (local dev test orders): accept only test ids.
        return order_id.startswith("order_TEST_") and payment_id.startswith("pay_TEST_")
    if order_id.startswith("order_TEST_"):
        return False
    body = f"{order_id}|{payment_id}"
    expected = hmac.new(settings.RAZORPAY_KEY_SECRET.encode(), body.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def verify_webhook_signature(body: bytes, signature: str) -> bool:
    secret = settings.RAZORPAY_WEBHOOK_SECRET or settings.RAZORPAY_KEY_SECRET
    if not secret:
        return False
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature or "")
