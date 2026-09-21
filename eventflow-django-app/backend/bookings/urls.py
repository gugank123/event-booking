from django.urls import path

from .views import BookingCancelView, BookingCheckInView, BookingCreateView, BookingLookupView, MyBookingsView

urlpatterns = [
    path("", BookingCreateView.as_view(), name="booking-create"),
    path("mine/", MyBookingsView.as_view(), name="booking-mine"),
    path("lookup/", BookingLookupView.as_view(), name="booking-lookup"),
    path("<int:pk>/cancel/", BookingCancelView.as_view(), name="booking-cancel"),
    path("<int:pk>/check-in/", BookingCheckInView.as_view(), name="booking-check-in"),
]
