from django.contrib import admin

from .models import Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("reference", "user", "event", "ticket_type", "quantity", "total_amount", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("reference", "user__email", "event__title")
