from rest_framework import mixins, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated

from accounts.models import User

from .audit import record_audit
from .models import SupportTicket
from .serializers import SupportTicketSerializer


class SupportTicketViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = SupportTicketSerializer
    queryset = SupportTicket.objects.none()
    permission_classes = (IsAuthenticated,)
    filterset_fields = ("status", "assigned_to")
    search_fields = ("subject", "message", "customer__phone", "customer__name")
    ordering_fields = ("created_at", "updated_at")

    def get_queryset(self):
        user = self.request.user
        queryset = SupportTicket.objects.select_related("customer", "assigned_to")
        if not user.is_authenticated:
            return queryset.none()
        if user.is_superuser or user.role in (User.Role.ADMIN, User.Role.SUPPORT):
            return queryset
        return queryset.filter(customer=user)

    def perform_create(self, serializer):
        ticket = serializer.save(
            customer=self.request.user,
            assigned_to=None,
            status=SupportTicket.Status.OPEN,
            response="",
        )
        record_audit(
            request=self.request,
            actor=self.request.user,
            action="support.ticket_created",
            target=ticket,
        )

    def perform_update(self, serializer):
        user = self.request.user
        if not (user.is_superuser or user.role in (User.Role.ADMIN, User.Role.SUPPORT)):
            raise PermissionDenied("فقط واحد پشتیبانی می‌تواند تیکت را به‌روزرسانی کند.")
        ticket = serializer.save()
        record_audit(
            request=self.request,
            actor=user,
            action="support.ticket_updated",
            target=ticket,
            metadata={"status": ticket.status},
        )
