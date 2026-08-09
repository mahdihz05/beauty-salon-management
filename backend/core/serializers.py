from rest_framework import serializers

from accounts.models import User

from .models import SupportTicket


class SupportTicketSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    customer_phone = serializers.CharField(source="customer.phone", read_only=True)
    assigned_to_name = serializers.CharField(source="assigned_to.name", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    assigned_to = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role=User.Role.SUPPORT), required=False, allow_null=True
    )

    class Meta:
        model = SupportTicket
        fields = (
            "id",
            "customer",
            "customer_name",
            "customer_phone",
            "assigned_to",
            "assigned_to_name",
            "subject",
            "message",
            "response",
            "status",
            "status_label",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "customer",
            "customer_name",
            "customer_phone",
            "assigned_to_name",
            "status_label",
            "created_at",
            "updated_at",
        )
