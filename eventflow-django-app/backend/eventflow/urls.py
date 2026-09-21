from django.contrib import admin
from django.urls import include, path

from .admin_api import AdminEventsView, AdminStatsView, AdminUsersView, AdminUserUpdateView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("accounts.urls")),
    path("api/events/", include("events.urls")),
    path("api/bookings/", include("bookings.urls")),
    path("api/comms/", include("comms.urls")),
    path("api/admin/stats/", AdminStatsView.as_view(), name="admin-stats"),
    path("api/admin/users/", AdminUsersView.as_view(), name="admin-users"),
    path("api/admin/users/<int:pk>/", AdminUserUpdateView.as_view(), name="admin-user-update"),
    path("api/admin/events/", AdminEventsView.as_view(), name="admin-events"),
]
