from rest_framework.permissions import SAFE_METHODS, BasePermission

from .models import BranchMembership, User


class HasAnyRole(BasePermission):
    allowed_roles: tuple[str, ...] = ()

    def has_permission(self, request, view):
        roles = getattr(view, "allowed_roles", self.allowed_roles)
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.is_superuser or request.user.role in roles)
        )


class IsPlatformAdmin(HasAnyRole):
    allowed_roles = (User.Role.ADMIN,)


class HasBranchAccess(BasePermission):
    """Limit branch resources to platform admins, owners, or active branch members."""

    def _branch_id(self, view, obj=None):
        if obj is not None:
            if hasattr(obj, "branch_id"):
                return obj.branch_id
            if hasattr(obj, "staff_id"):
                return obj.staff.branch_id
            if hasattr(obj, "branch_service_id"):
                return obj.branch_service.branch_id
            return getattr(obj, "pk", None)
        return view.kwargs.get("branch_pk") or view.kwargs.get("branch_id")

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser or request.user.role == User.Role.ADMIN:
            return True
        branch_id = self._branch_id(view)
        if branch_id is None:
            return True
        return self._can_access(request.user, branch_id)

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser or request.user.role == User.Role.ADMIN:
            return True
        branch_id = self._branch_id(view, obj)
        if request.method in SAFE_METHODS:
            return self._can_access(request.user, branch_id)
        return self._can_manage(request.user, branch_id)

    @staticmethod
    def _can_access(user, branch_id) -> bool:
        if user.owned_salons.filter(branches__id=branch_id).exists():
            return True
        return BranchMembership.objects.filter(
            user=user, branch_id=branch_id, is_active=True
        ).exists()

    @staticmethod
    def _can_manage(user, branch_id) -> bool:
        if user.is_superuser or user.role == User.Role.ADMIN:
            return True
        if user.owned_salons.filter(branches__id=branch_id).exists():
            return True
        return BranchMembership.objects.filter(
            user=user,
            branch_id=branch_id,
            role=BranchMembership.Role.MANAGER,
            is_active=True,
        ).exists()
