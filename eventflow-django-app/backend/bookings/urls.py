from django.urls import path

from .views import (
    BookingCancelView,
    BookingCheckInView,
    BookingCreateView,
    BookingDetailView,
    BookingLookupView,
    MyBookingsView,
    SeatHoldView,
)

urlpatterns = [
    path("", BookingCreateView.as_view(), name="booking-create"),
    path("holds/", SeatHoldView.as_view(), name="seat-hold"),
    path("mine/", MyBookingsView.as_view(), name="booking-mine"),
    path("lookup/", BookingLookupView.as_view(), name="booking-lookup"),
    path("<int:pk>/", BookingDetailView.as_view(), name="booking-detail"),
    path("<int:pk>/cancel/", BookingCancelView.as_view(), name="booking-cancel"),
    path("<int:pk>/check-in/", BookingCheckInView.as_view(), name="booking-check-in"),
]
