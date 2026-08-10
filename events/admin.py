from django.contrib import admin

from .models import Event


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'date', 'time', 'venue', 'price')
    list_filter = ('category', 'date')
    search_fields = ('title', 'venue', 'description')
    ordering = ('date',)
