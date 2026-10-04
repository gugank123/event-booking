from django.contrib import admin

from .models import AuditLog, EmailVerification, OrganizerProfile, PasswordResetToken, User, UserProfile


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("email", "role", "email_verified", "is_active", "date_joined")
    list_filter = ("role", "email_verified", "is_active")
    search_fields = ("email", "first_name", "last_name")


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "phone", "city")
    search_fields = ("user__email", "phone")


@admin.register(OrganizerProfile)
class OrganizerProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "organization_name", "contact_phone")
    search_fields = ("user__email", "organization_name")


@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    list_display = ("user", "expires_at", "attempts", "consumed_at", "created_at")
    search_fields = ("user__email",)


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "expires_at", "used_at", "created_at")
    search_fields = ("user__email",)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("action", "user", "object_type", "object_id", "ip_address", "created_at")
    list_filter = ("action",)
    search_fields = ("user__email", "action", "object_id")
    readonly_fields = ("user", "action", "object_type", "object_id", "ip_address", "metadata", "created_at")

    def has_add_permission(self, request):
        return False
