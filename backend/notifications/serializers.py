from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    event_label = serializers.CharField(source="get_event_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    customer_name = serializers.CharField(source="recipient.name", read_only=True)
    customer_phone = serializers.CharField(source="recipient.phone", read_only=True)
    salon_name = serializers.CharField(source="booking.branch.salon.name", read_only=True)

    class Meta:
        model = Notification
        fields = (
            "id",
            "booking",
            "event",
            "event_label",
            "channel",
            "status",
            "status_label",
            "customer_name",
            "customer_phone",
            "salon_name",
            "message",
            "provider_ref",
            "error",
            "created_at",
            "sent_at",
        )
