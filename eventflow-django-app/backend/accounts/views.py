from django.conf import settings
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User
from .serializers import LoginSerializer, RegisterSerializer, UserSerializer


def tokens_for(user):
    refresh = RefreshToken.for_user(user)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        from comms.emails import send_welcome_email

        send_welcome_email(user)
        return Response({**tokens_for(user), "user": UserSerializer(user).data}, status=201)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        return Response({**tokens_for(user), "user": UserSerializer(user).data})


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"user": UserSerializer(request.user).data})


class GoogleLoginView(APIView):
    """Real Google Sign-In.

    The frontend signs the user in with Google Identity Services and POSTs
    {"idToken": "<Google ID token>", "role": "attendee"|"organizer"} here.
    We cryptographically verify the token against GOOGLE_OAUTH_CLIENT_ID,
    then find-or-create the matching account and return our own JWT pair.
    """

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
            )
            user.set_unusable_password()
            user.save()
            from comms.emails import send_welcome_email

            send_welcome_email(user)
        elif not user.is_active:
            return Response({"error": "This account has been suspended."}, status=403)

        return Response({**tokens_for(user), "user": UserSerializer(user).data})
