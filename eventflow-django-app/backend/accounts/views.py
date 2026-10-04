import logging

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import serializers as drf_serializers
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import AuditLog, EmailVerification, PasswordResetToken, User
from .serializers import LoginSerializer, RegisterSerializer, UserSerializer, tokens_for

logger = logging.getLogger(__name__)


class _RegisterRequest(drf_serializers.Serializer):
    name = drf_serializers.CharField()
    email = drf_serializers.EmailField()
    phone = drf_serializers.CharField(required=False, allow_blank=True)
    password = drf_serializers.CharField()
    role = drf_serializers.ChoiceField(choices=["attendee", "organizer"], required=False)


class _VerifyRequest(drf_serializers.Serializer):
    email = drf_serializers.EmailField()
    code = drf_serializers.CharField(max_length=6)


class _EmailRequest(drf_serializers.Serializer):
    email = drf_serializers.EmailField()


class _LoginRequest(drf_serializers.Serializer):
    email = drf_serializers.EmailField()
    password = drf_serializers.CharField()


class _ResetRequest(drf_serializers.Serializer):
    token = drf_serializers.CharField()
    password = drf_serializers.CharField()
    confirm_password = drf_serializers.CharField()


class AuthThrottle(AnonRateThrottle):
    scope = "auth"


class EmailThrottle(AnonRateThrottle):
    scope = "email"


def _ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _audit(user, action, request=None, **meta):
    try:
        AuditLog.objects.create(
            user=user if getattr(user, "is_authenticated", False) else None,
            action=action, object_type="", object_id="",
            ip_address=_ip(request) if request else None, metadata=meta)
    except Exception:
        logger.exception("audit failed %s", action)


class RegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthThrottle]

    @extend_schema(request=_RegisterRequest, tags=["auth"],
                   description="Register (unverified). A 6-digit code is emailed; verify before login.")
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        from comms.emails import send_verification_email

        _, code = EmailVerification.issue(user)
        send_verification_email(user, code)
        _audit(user, "auth.register", request, email=user.email)
        logger.info("registered user id=%s email=%s", user.id, user.email)
        # Unverified: return NO tokens until email is verified.
        return Response({"user": UserSerializer(user).data,
                         "detail": "Account created. Enter the 6-digit code sent to your email.",
                         "needs_verification": True}, status=201)


class VerifyEmailView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthThrottle]

    @extend_schema(request=_VerifyRequest, tags=["auth"],
                   description="Verify email with the 6-digit code. Returns JWT pair on success.")
    def post(self, request):
        email = (request.data.get("email") or "").strip().lower()
        code = (request.data.get("code") or "").strip()
        if not email or not code:
            return Response({"error": "Email and 6-digit code are required."}, status=400)
        user = User.objects.filter(email=email).first()
        if user is None:
            return Response({"error": "Invalid code."}, status=400)
        if user.email_verified:
            return Response({"user": UserSerializer(user).data, **tokens_for(user)})
        latest = EmailVerification.objects.filter(
            user=user, consumed_at__isnull=True).order_by("-created_at").first()
        if latest is None or not latest.is_valid:
            return Response({"error": "Code expired. Request a new one."}, status=400)
        if not latest.verify_code(code):
            left = max(0, latest.max_attempts - latest.attempts)
            _audit(user, "auth.verify_failed", request, email=email)
            return Response({"error": f"Incorrect code. {left} attempt(s) left."}, status=400)
        user.email_verified = True
        user.save(update_fields=["email_verified"])
        from comms.emails import send_welcome_email

        send_welcome_email(user)
        _audit(user, "auth.verified", request, email=email)
        return Response({**tokens_for(user), "user": UserSerializer(user).data})


class ResendVerificationView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [EmailThrottle]

    @extend_schema(request=_EmailRequest, tags=["auth"])
    def post(self, request):
        from datetime import timedelta

        email = (request.data.get("email") or "").strip().lower()
        if not email:
            return Response({"error": "Email is required."}, status=400)
        user = User.objects.filter(email=email).first()
        # Same response whether or not the account exists (anti-enumeration),
        # except we still send the mail when it does.
        if user is not None and not user.email_verified:
            last = EmailVerification.objects.filter(user=user).order_by("-created_at").first()
            if last and (timezone.now() - last.created_at) < timedelta(seconds=60):
                return Response({"error": "Please wait a minute before requesting a new code."}, status=429)
            from comms.emails import send_verification_email

            _, code = EmailVerification.issue(user)
            send_verification_email(user, code)
        return Response({"detail": "If an unverified account exists for that email, a new code was sent."})


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthThrottle]

    @extend_schema(request=_LoginRequest, tags=["auth"],
                   description="Login. Blocked until email_verified (except Google accounts).")
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        _audit(user, "auth.login", request)
        logger.info("login user id=%s", user.id)
        return Response({**tokens_for(user), "user": UserSerializer(user).data})


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh = (request.data.get("refresh") or "").strip()
        if refresh:
            try:
                RefreshToken(refresh).blacklist()
            except Exception:
                pass
        _audit(request.user, "auth.logout", request)
        return Response({"detail": "Logged out."})


class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [EmailThrottle]

    @extend_schema(request=_EmailRequest, tags=["auth"],
                   description="Request a reset link. Same response whether the email exists.")
    def post(self, request):
        email = (request.data.get("email") or "").strip().lower()
        # Always return the same message — never reveal whether an email exists.
        user = User.objects.filter(email=email).first() if email else None
        if user is not None and user.is_active:
            from comms.emails import send_password_reset_email

            _, raw = PasswordResetToken.issue(user)
            send_password_reset_email(user, raw)
            _audit(user, "auth.password_reset_requested", request)
        return Response({"detail": "If an account exists for that email, a reset link was sent."})


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthThrottle]

    @extend_schema(request=_ResetRequest, tags=["auth"],
                   description="Set a new password with a single-use token (30 min expiry).")
    def post(self, request):
        token = (request.data.get("token") or "").strip()
        password = request.data.get("password") or ""
        password2 = request.data.get("confirm_password") or request.data.get("password2") or ""
        if not token:
            return Response({"error": "Reset token is required."}, status=400)
        if password != password2 and password2:
            return Response({"error": "Passwords do not match."}, status=400)
        try:
            validate_password(password)
        except DjangoValidationError as exc:
            return Response({"error": "; ".join(exc.messages)}, status=400)
        reset = PasswordResetToken.lookup(token)
        if reset is None or not reset.is_valid:
            return Response({"error": "This reset link is invalid or expired."}, status=400)
        user = reset.user
        user.set_password(password)
        user.save(update_fields=["password"])
        reset.used_at = timezone.now()
        reset.save(update_fields=["used_at"])
        # Invalidate all other outstanding reset tokens for this user.
        PasswordResetToken.objects.filter(user=user, used_at__isnull=True).exclude(pk=reset.pk).update(
            used_at=timezone.now())
        _audit(user, "auth.password_reset_completed", request)
        logger.info("password reset completed user id=%s", user.id)
        return Response({"detail": "Password updated. Please log in."})


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"user": UserSerializer(request.user).data})


class GoogleLoginView(APIView):
    """Real Google Sign-In. Frontend posts {idToken}; we verify server-side."""

    permission_classes = [AllowAny]

    def post(self, request):
        token = (request.data.get("idToken") or "").strip()
        if not token:
            return Response({"error": "No Google credential was provided."}, status=400)
        if not settings.GOOGLE_OAUTH_CLIENT_ID:
            return Response(
                {"error": "Google sign-in isn't configured on the server yet. Set GOOGLE_OAUTH_CLIENT_ID."},
                status=503,
            )

        from google.auth.transport import requests as google_requests
        from google.oauth2 import id_token as google_id_token

        try:
            claims = google_id_token.verify_oauth2_token(
                token, google_requests.Request(), settings.GOOGLE_OAUTH_CLIENT_ID
            )
        except Exception:
            return Response({"error": "That Google sign-in couldn't be verified. Try again."}, status=401)

        email = (claims.get("email") or "").strip().lower()
        if not email or not claims.get("email_verified"):
            return Response({"error": "Google didn't confirm a verified email address."}, status=401)

        first_name = (claims.get("given_name") or "").strip()
        last_name = (claims.get("family_name") or "").strip()

        user = User.objects.filter(email=email).first()
        created = user is None
        if created:
            requested_role = (request.data.get("role") or User.Role.ATTENDEE).strip().lower()
            role = requested_role if requested_role in (User.Role.ATTENDEE, User.Role.ORGANIZER) else User.Role.ATTENDEE
            user = User(
                username=email,
                email=email,
                first_name=first_name[:150],
                last_name=last_name[:150],
                role=role,
                email_verified=True,
            )
            user.set_unusable_password()
            user.save()
            from comms.emails import send_welcome_email

            send_welcome_email(user)
            _audit(user, "auth.google_register", request, email=email)
        elif not user.is_active:
            return Response({"error": "This account has been suspended."}, status=403)
        else:
            if not user.email_verified:
                user.email_verified = True
                user.save(update_fields=["email_verified"])
            _audit(user, "auth.google_login", request)

        return Response({**tokens_for(user), "user": UserSerializer(user).data})
