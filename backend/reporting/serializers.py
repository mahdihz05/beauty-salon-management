from rest_framework import serializers


class ReportQuerySerializer(serializers.Serializer):
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    branch = serializers.IntegerField(required=False, min_value=1)

    def validate(self, attrs):
        if (
            attrs.get("date_from")
            and attrs.get("date_to")
            and attrs["date_to"] < attrs["date_from"]
        ):
            raise serializers.ValidationError("تاریخ پایان باید بعد از تاریخ شروع باشد.")
        return attrs


class DailyMetricSerializer(serializers.Serializer):
    date = serializers.DateField()
    bookings = serializers.IntegerField()
    revenue = serializers.IntegerField()


class TopServiceSerializer(serializers.Serializer):
    service_name = serializers.CharField()
    count = serializers.IntegerField()
    revenue = serializers.IntegerField()


class ReportSummarySerializer(serializers.Serializer):
    date_from = serializers.DateField()
    date_to = serializers.DateField()
    gross_revenue = serializers.IntegerField()
    commission = serializers.IntegerField()
    net_revenue = serializers.IntegerField()
    booking_count = serializers.IntegerField()
    completed_count = serializers.IntegerField()
    cancelled_count = serializers.IntegerField()
    no_show_count = serializers.IntegerField()
    average_booking_value = serializers.IntegerField()
    daily = DailyMetricSerializer(many=True)
    top_services = TopServiceSerializer(many=True)
