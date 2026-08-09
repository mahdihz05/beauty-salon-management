from django.db.models import Sum
from rest_framework import serializers

from payments.models import Payment
from salons.models import Branch

from .models import Booking, BookingItem, DiscountCode


class AvailabilityQuerySerializer(serializers.Serializer):
    branch = serializers.PrimaryKeyRelatedField(queryset=Branch.objects.filter(is_active=True))
    services = serializers.CharField(help_text="شناسه خدمات شعبه، جداشده با کاما")
    staff = serializers.IntegerField(required=False, min_value=1)
    date = serializers.DateField()

    def validate_services(self, value):
        try:
            service_ids = [int(item) for item in value.split(",") if item]
        except ValueError as exc:
            raise serializers.ValidationError("شناسه خدمات نامعتبر است.") from exc
        if not service_ids:
            raise serializers.ValidationError("حداقل یک خدمت انتخاب کنید.")
        return service_ids


class AvailableSlotSerializer(serializers.Serializer):
    start_at = serializers.DateTimeField()
    end_at = serializers.DateTimeField()
    staff_id = serializers.IntegerField()
    staff_name = serializers.CharField()
    total_price = serializers.IntegerField()
    duration_minutes = serializers.IntegerField()


class CreateHoldSerializer(serializers.Serializer):
    branch = serializers.PrimaryKeyRelatedField(queryset=Branch.objects.filter(is_active=True))
    service_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), min_length=1)
    staff_id = serializers.IntegerField(min_value=1)
    start_at = serializers.DateTimeField()
    notes = serializers.CharField(required=False, allow_blank=True, max_length=1000)


class CreateManualBookingSerializer(CreateHoldSerializer):
    customer_phone = serializers.CharField(max_length=20)
    customer_name = serializers.CharField(required=False, allow_blank=True, max_length=150)


class BookingItemSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source="branch_service.service.name", read_only=True)
    staff_name = serializers.CharField(source="staff.full_name", read_only=True)

    class Meta:
        model = BookingItem
        fields = (
            "id",
            "branch_service",
            "service_name",
            "staff",
            "staff_name",
            "price",
            "duration_minutes",
        )


class BookingSerializer(serializers.ModelSerializer):
    items = BookingItemSerializer(many=True, read_only=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    salon_name = serializers.CharField(source="branch.salon.name", read_only=True)
    staff_name = serializers.CharField(source="staff.full_name", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    paid_amount = serializers.SerializerMethodField()
    remaining_amount = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = (
            "id",
            "customer",
            "branch",
            "branch_name",
            "salon_name",
            "staff",
            "staff_name",
            "status",
            "status_label",
            "start_at",
            "end_at",
            "total_price",
            "deposit_amount",
            "discount_code",
            "discount_amount",
            "paid_amount",
            "remaining_amount",
            "notes",
            "hold_expires_at",
            "cancelled_at",
            "cancellation_reason",
            "items",
            "created_at",
        )
        read_only_fields = fields

    def get_paid_amount(self, obj) -> int:
        prefetched = getattr(obj, "_prefetched_objects_cache", {}).get("payments")
        if prefetched is not None:
            return sum(item.amount for item in prefetched if item.status == Payment.Status.PAID)
        return (
            obj.payments.filter(status=Payment.Status.PAID).aggregate(total=Sum("amount"))["total"]
            or 0
        )

    def get_remaining_amount(self, obj) -> int:
        return max(obj.total_price - self.get_paid_amount(obj), 0)


class DiscountCodeSerializer(serializers.ModelSerializer):
    salon_name = serializers.CharField(source="salon.name", read_only=True)
    type_label = serializers.CharField(source="get_type_display", read_only=True)

    class Meta:
        model = DiscountCode
        fields = (
            "id",
            "code",
            "salon",
            "salon_name",
            "type",
            "type_label",
            "value",
            "minimum_purchase",
            "maximum_discount",
            "usage_limit",
            "used_count",
            "starts_at",
            "ends_at",
            "is_active",
            "created_at",
        )
        read_only_fields = ("id", "used_count", "created_at")

    def validate(self, attrs):
        discount_type = attrs.get("type", getattr(self.instance, "type", None))
        value = attrs.get("value", getattr(self.instance, "value", 0))
        starts_at = attrs.get("starts_at", getattr(self.instance, "starts_at", None))
        ends_at = attrs.get("ends_at", getattr(self.instance, "ends_at", None))
        if discount_type == DiscountCode.Type.PERCENT and value > 100:
            raise serializers.ValidationError({"value": "درصد تخفیف نمی‌تواند بیش از ۱۰۰ باشد."})
        if starts_at and ends_at and ends_at <= starts_at:
            raise serializers.ValidationError({"ends_at": "پایان باید بعد از شروع باشد."})
        request = self.context["request"]
        salon = attrs.get("salon", getattr(self.instance, "salon", None))
        if salon is None and not (request.user.is_superuser or request.user.role == "admin"):
            raise serializers.ValidationError({"salon": "فقط مدیر کل می‌تواند کد سراسری بسازد."})
        if salon and not (
            request.user.is_superuser
            or request.user.role == "admin"
            or salon.owner_id == request.user.id
        ):
            raise serializers.ValidationError({"salon": "به این سالن دسترسی ندارید."})
        attrs["code"] = attrs.get("code", self.instance.code if self.instance else "").upper()
        return attrs


class CustomerSummarySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    phone = serializers.CharField()
    booking_count = serializers.IntegerField()
    total_spent = serializers.IntegerField()
    last_booking_at = serializers.DateTimeField(allow_null=True)
