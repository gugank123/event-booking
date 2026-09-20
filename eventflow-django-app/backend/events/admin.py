from django.contrib import admin

from .models import Event, TicketType


class TicketTypeInline(admin.TabularInline):
    model = TicketType
    extra = 1


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "organizer", "category", "city", "starts_at", "status")
    list_filter = ("status", "category")
    search_fields = ("title", "venue", "city")
    inlines = [TicketTypeInline]
