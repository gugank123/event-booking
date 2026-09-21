from django.contrib import admin

from .models import (
    Announcement,
    Conversation,
    ConversationMessage,
    FAQ,
    Invitation,
    Notification,
    Report,
    SupportMessage,
    SupportTicket,
)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "category", "title", "is_read", "created_at")
    list_filter = ("category", "is_read", "created_at")
    search_fields = ("title", "message", "user__email")
    readonly_fields = ("created_at",)


class ConversationMessageInline(admin.TabularInline):
    model = ConversationMessage
    extra = 0
    readonly_fields = ("sender", "body", "is_read", "created_at")


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "subject", "customer", "organizer", "event", "topic", "status", "updated_at")
    list_filter = ("status", "topic", "created_at")
    search_fields = ("subject", "customer__email", "organizer__email", "event__title")
    inlines = [ConversationMessageInline]


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ("id", "email", "event", "status", "expires_at", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("email", "event__title", "token")
    readonly_fields = ("token", "created_at")


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "event", "organizer", "send_email", "send_in_app", "created_at")
    list_filter = ("created_at",)
    search_fields = ("title", "message", "event__title")


class SupportMessageInline(admin.TabularInline):
    model = SupportMessage
    extra = 0
    readonly_fields = ("sender", "body", "created_at")


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ("id", "subject", "user", "category", "priority", "status", "assigned_to", "updated_at")
    list_filter = ("status", "priority", "category", "created_at")
    search_fields = ("subject", "description", "user__email")
    inlines = [SupportMessageInline]


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ("id", "category", "question", "order", "is_published", "updated_at")
    list_filter = ("category", "is_published")
    search_fields = ("question", "answer")


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("id", "subject", "user", "category", "status", "created_at")
    list_filter = ("status", "category", "created_at")
    search_fields = ("subject", "description", "user__email")
