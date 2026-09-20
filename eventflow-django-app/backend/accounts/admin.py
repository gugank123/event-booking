from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ("email", "first_name", "last_name", "role", "is_active", "date_joined")
    fieldsets = UserAdmin.fieldsets + (("EventFlow", {"fields": ("role",)}),)
