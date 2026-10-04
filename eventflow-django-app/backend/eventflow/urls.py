from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.db import connection
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .admin_api import AdminEventsView, AdminStatsView, AdminUsersView, AdminUserUpdateView, AuditLogListView


class HealthView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        db_ok = True
        try:
            with connection.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        except Exception:
            db_ok = False
        return Response({"status": "healthy" if db_ok else "degraded", "db": "up" if db_ok else "down"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", HealthView.as_view(), name="health"),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    path("api/auth/", include("accounts.urls")),
    path("api/events/", include("events.urls")),
    path("api/bookings/", include("bookings.urls")),
    path("api/payments/", include("payments.urls")),
    path("api/comms/", include("comms.urls")),
    path("api/admin/stats/", AdminStatsView.as_view(), name="admin-stats"),
    path("api/admin/users/", AdminUsersView.as_view(), name="admin-users"),
    path("api/admin/users/<int:pk>/", AdminUserUpdateView.as_view(), name="admin-user-update"),
    path("api/admin/events/", AdminEventsView.as_view(), name="admin-events"),
    path("api/admin/audit-logs/", AuditLogListView.as_view(), name="admin-audit-logs"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
