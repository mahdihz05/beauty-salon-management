from rest_framework.permissions import BasePermission

from accounts.models import User


class IsSalonOwnerOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        salon = getattr(obj, "salon", obj)
        if hasattr(salon, "branch"):
            salon = salon.branch.salon
        return bool(
            request.user.is_superuser
            or request.user.role == User.Role.ADMIN
            or salon.owner_id == request.user.id
        )
