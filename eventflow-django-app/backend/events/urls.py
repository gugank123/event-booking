from django.urls import path

from .views import (
    EventBookingsView,
    EventCategoriesView,
    EventDetailView,
    EventListCreateView,
    TicketTypeCreateView,
)

urlpatterns = [
    path("", EventListCreateView.as_view(), name="event-list-create"),
    path("categories/", EventCategoriesView.as_view(), name="event-categories"),
    path("<int:pk>/", EventDetailView.as_view(), name="event-detail"),
    path("<int:pk>/ticket-types/", TicketTypeCreateView.as_view(), name="event-ticket-types"),
    path("<int:pk>/bookings/", EventBookingsView.as_view(), name="event-bookings"),
]
