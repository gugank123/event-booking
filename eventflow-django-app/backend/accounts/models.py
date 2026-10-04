import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    class Role(models.TextChoices):
        ATTENDEE = "attendee", "Attendee"
        ORGANIZER = "organizer", "Organizer"
        ADMIN = "admin", "Admin"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.ATTENDEE)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True, default="")
    # Email must be verified before the account can book. Google accounts are
    # created pre-verified; password accounts verify via 6-digit code.
    email_verified = models.BooleanField(default=False)
    # Suspension re-uses Django's built-in is_active flag: a suspended user
    # simply cannot authenticate, which Django already enforces everywhere.
    #
    # Login is by email. We keep AbstractUser's `username` field (so we don't
    # need a custom UserManager) but always set it equal to the email at
    # registration time, and authenticate against that.

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.role})"


class UserProfile(models.Model):
    """Extended customer profile (one-to-one with User)."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    phone = models.CharField(max_length=20, blank=True, default="")
    city = models.CharField(max_length=120, blank=True, default="")
    avatar_url = models.URLField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile of {self.user.email}"


class OrganizerProfile(models.Model):
    """KYC / payout-relevant organizer details. No bank secrets stored here."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="organizer_profile"
    )
    organization_name = models.CharField(max_length=200, blank=True, default="")
    contact_phone = models.CharField(max_length=20, blank=True, default="")
    website = models.URLField(blank=True, default="")
    upi_vpa = models.CharField(max_length=100, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Organizer profile of {self.user.email}"


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


class EmailVerification(models.Model):
    """Hashed 6-digit email verification code with expiry, attempts + resend limits."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="email_codes")
    code_hash = models.CharField(max_length=64)
    expires_at = models.DateTimeField()
    attempts = models.PositiveIntegerField(default=0)
    max_attempts = models.PositiveIntegerField(default=5)
    consumed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "-created_at"])]

    @classmethod
    def issue(cls, user, ttl_minutes=15):
        # Invalidate previous unconsumed codes.
        cls.objects.filter(user=user, consumed_at__isnull=True).update(consumed_at=timezone.now())
        code = f"{secrets.randbelow(900000) + 100000:06d}"
        obj = cls.objects.create(
            user=user,
            code_hash=_hash_code(code),
            expires_at=timezone.now() + timedelta(minutes=ttl_minutes),
        )
        return obj, code

    def verify_code(self, code: str) -> bool:
        if self.consumed_at or timezone.now() > self.expires_at or self.attempts >= self.max_attempts:
            return False
        # Constant-time compare of hashes.
        import hmac

        ok = hmac.compare_digest(self.code_hash, _hash_code(code.strip()))
        self.attempts += 1
        if ok:
            self.consumed_at = timezone.now()
        self.save(update_fields=["attempts", "consumed_at"])
        return ok

    @property
    def is_valid(self):
        return (
            self.consumed_at is None
            and timezone.now() <= self.expires_at
            and self.attempts < self.max_attempts
        )


class PasswordResetToken(models.Model):
    """Single-use hashed password-reset token with expiry."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reset_tokens")
    token_hash = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["token_hash"])]

    @classmethod
    def issue(cls, user, ttl_minutes=30):
        raw = secrets.token_urlsafe(32)
        obj = cls.objects.create(
            user=user,
            token_hash=hashlib.sha256(raw.encode()).hexdigest(),
            expires_at=timezone.now() + timedelta(minutes=ttl_minutes),
        )
        return obj, raw

    @classmethod
    def lookup(cls, raw: str):
        h = hashlib.sha256(raw.encode()).hexdigest()
        try:
            return cls.objects.select_related("user").get(token_hash=h)
        except cls.DoesNotExist:
            return None

    @property
    def is_valid(self):
        return self.used_at is None and timezone.now() <= self.expires_at


class AuditLog(models.Model):
    """Immutable record of security-relevant actions (no sensitive payload data)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="audit_logs"
    )
    action = models.CharField(max_length=80, db_index=True)
    object_type = models.CharField(max_length=80, blank=True, default="")
    object_id = models.CharField(max_length=80, blank=True, default="")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action} by {self.user_id} @ {self.created_at:%Y-%m-%d %H:%M}"
