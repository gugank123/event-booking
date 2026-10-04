from django.contrib import admin

from .models import Event, EventCategory, Seat, SeatHold, TicketType, Venue


class TicketTypeInline(admin.TabularInline):
    model = TicketType
    extra = 1


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "organizer", "category", "city", "starts_at", "status", "seating_type")
    list_filter = ("status", "category", "seating_type")
    search_fields = ("title", "venue", "city")
    inlines = [TicketTypeInline]


@admin.register(Seat)
class SeatAdmin(admin.ModelAdmin):
    list_display = ("event", "section", "row_label", "number", "price", "status", "held_until")
    list_filter = ("status", "section")
    search_fields = ("event__title", "section", "row_label")


@admin.register(SeatHold)
class SeatHoldAdmin(admin.ModelAdmin):
    list_display = ("id", "event", "user", "status", "expires_at", "created_at")
    list_filter = ("status",)
    search_fields = ("event__title", "user__email")


@admin.register(EventCategory)
class EventCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ("name", "city", "capacity")
    search_fields = ("name", "city")
