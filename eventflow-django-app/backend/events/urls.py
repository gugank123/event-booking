from django.urls import path

from .views import (
    EventBookingsView,
    EventCategoriesView,
    EventDetailView,
    EventDuplicateView,
    EventImageUploadView,
    EventListCreateView,
    EventReviewsView,
    EventSeatSetupView,
    EventWishlistView,
    OrganizerDashboardView,
    ReviewDetailView,
    TicketTypeCreateView,
    WishlistView,
)

urlpatterns = [
    path("", EventListCreateView.as_view(), name="event-list-create"),
    path("categories/", EventCategoriesView.as_view(), name="event-categories"),
    path("organizer/dashboard/", OrganizerDashboardView.as_view(), name="organizer-dashboard"),
    path("wishlist/", WishlistView.as_view(), name="event-wishlist"),
    path("<int:pk>/", EventDetailView.as_view(), name="event-detail"),
    path("<int:pk>/ticket-types/", TicketTypeCreateView.as_view(), name="event-ticket-types"),
    path("<int:pk>/bookings/", EventBookingsView.as_view(), name="event-bookings"),
    path("<int:pk>/wishlist/", EventWishlistView.as_view(), name="event-wishlist-toggle"),
    path("<int:pk>/reviews/", EventReviewsView.as_view(), name="event-reviews"),
    path("<int:pk>/duplicate/", EventDuplicateView.as_view(), name="event-duplicate"),
    path("<int:pk>/seats/", EventSeatSetupView.as_view(), name="event-seats"),
    path("<int:pk>/image/", EventImageUploadView.as_view(), name="event-image"),
    path("reviews/<int:pk>/", ReviewDetailView.as_view(), name="review-detail"),
]
