from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    CookieTokenRefreshView,
    ForgotPasswordView,
    GoogleLoginView,
    LoginView,
    LogoutView,
    MeView,
    RegisterView,
    ResendVerificationView,
    ResetPasswordView,
    VerifyEmailView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("verify-email/", VerifyEmailView.as_view(), name="verify-email"),
    path("resend-verification/", ResendVerificationView.as_view(), name="resend-verification"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("google/", GoogleLoginView.as_view(), name="google-login"),
    path("me/", MeView.as_view(), name="me"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("refresh/", CookieTokenRefreshView.as_view(), name="refresh"),
    path("forgot-password/", ForgotPasswordView.as_view(), name="forgot-password"),
    path("reset-password/", ResetPasswordView.as_view(), name="reset-password"),
]
