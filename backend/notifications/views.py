from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from accounts.models import User
from salons.views import manageable_branch_ids

from .models import Notification
from .serializers import NotificationSerializer


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = (IsAuthenticated,)
    serializer_class = NotificationSerializer
    filterset_fields = ("event", "status", "channel")
    ordering_fields = ("created_at", "sent_at")

    def get_queryset(self):
        queryset = Notification.objects.select_related("recipient", "booking__branch__salon")
        user = self.request.user
        if not user.is_authenticated:
            return queryset.none()
        if user.is_superuser or user.role == User.Role.ADMIN:
            return queryset
        branch_ids = manageable_branch_ids(user, include_receptionist=True)
        if branch_ids:
            return queryset.filter(booking__branch_id__in=branch_ids)
        return queryset.filter(recipient=user)
