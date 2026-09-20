from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsOrganizerOrAdmin(BasePermission):
    """Only organizers/admins may create events."""

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated and request.user.role in ("organizer", "admin"))


class IsEventOwnerOrAdmin(BasePermission):
    """Only the event's own organizer, or an admin, may edit/delete/view internals."""

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        user = request.user
        return bool(user and user.is_authenticated and (user.role == "admin" or obj.organizer_id == user.id))


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == "admin")
