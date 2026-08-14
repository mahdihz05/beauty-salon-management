from rest_framework import serializers

from .models import (
    Branch,
    BranchClosure,
    BranchService,
    City,
    District,
    Salon,
    SalonImage,
    Service,
    ServiceCategory,
    Staff,
    StaffService,
    StaffShift,
    StaffTimeOff,
)


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ("id", "name", "slug")


class DistrictSerializer(serializers.ModelSerializer):
    city_name = serializers.CharField(source="city.name", read_only=True)

    class Meta:
        model = District
        fields = ("id", "city", "city_name", "name", "slug")


class SalonImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalonImage
        fields = ("id", "salon", "image", "alt_text", "is_cover", "sort_order", "created_at")
        read_only_fields = ("id", "created_at")


class BranchSummarySerializer(serializers.ModelSerializer):
    city_name = serializers.CharField(source="city.name", read_only=True)

    class Meta:
        model = Branch
        fields = ("id", "name", "city_name", "address", "phone", "is_active")


class SalonSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source="owner.name", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    type_label = serializers.CharField(source="get_type_display", read_only=True)
    branches = BranchSummarySerializer(many=True, read_only=True)
    images = SalonImageSerializer(many=True, read_only=True)

    class Meta:
        model = Salon
        fields = (
            "id",
            "owner",
            "owner_name",
            "name",
            "slug",
            "type",
            "type_label",
            "description",
            "status",
            "status_label",
            "rejection_reason",
            "branches",
            "images",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "owner",
            "status",
            "rejection_reason",
            "created_at",
            "updated_at",
        )
        extra_kwargs = {"slug": {"required": False}}


class BranchSerializer(serializers.ModelSerializer):
    salon_name = serializers.CharField(source="salon.name", read_only=True)
    city_name = serializers.CharField(source="city.name", read_only=True)
    district_name = serializers.CharField(source="district.name", read_only=True)

    class Meta:
        model = Branch
        fields = (
            "id",
            "salon",
            "salon_name",
            "name",
            "city",
            "city_name",
            "district",
            "district_name",
            "address",
            "latitude",
            "longitude",
            "phone",
            "working_hours",
            "amenities",
            "slot_interval_minutes",
            "preparation_buffer_minutes",
            "deposit_percent",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate(self, attrs):
        city = attrs.get("city", getattr(self.instance, "city", None))
        district = attrs.get("district", getattr(self.instance, "district", None))
        if district and city and district.city_id != city.id:
            raise serializers.ValidationError(
                {"district": "منطقه باید متعلق به شهر انتخاب‌شده باشد."}
            )
        working_hours = attrs.get("working_hours")
        if working_hours is not None:
            attrs["working_hours"] = self._validate_working_hours(working_hours)
        return attrs

    @staticmethod
    def _validate_working_hours(value):
        if not isinstance(value, dict):
            raise serializers.ValidationError(
                {"working_hours": "ساعات کاری باید برای روزهای هفته ثبت شود."}
            )
        normalized = {}
        for day in range(7):
            raw = value.get(str(day), [])
            if isinstance(raw, dict):
                raw = [raw] if raw.get("is_open", False) else []
            elif isinstance(raw, list) and len(raw) == 2 and all(isinstance(v, str) for v in raw):
                raw = [{"start": raw[0], "end": raw[1]}]
            if not isinstance(raw, list):
                raise serializers.ValidationError(
                    {"working_hours": f"ساختار ساعات روز {day} معتبر نیست."}
                )
            windows = []
            for window in raw:
                if not isinstance(window, dict):
                    raise serializers.ValidationError(
                        {"working_hours": f"بازه روز {day} معتبر نیست."}
                    )
                start, end = window.get("start"), window.get("end")
                try:
                    from datetime import time

                    start_value, end_value = time.fromisoformat(start), time.fromisoformat(end)
                except (TypeError, ValueError):
                    raise serializers.ValidationError(
                        {"working_hours": "ساعت شروع و پایان باید معتبر باشد."}
                    ) from None
                if start_value >= end_value:
                    raise serializers.ValidationError(
                        {"working_hours": "ساعت پایان باید پس از ساعت شروع باشد."}
                    )
                windows.append((start_value, end_value, {"start": start[:5], "end": end[:5]}))
            windows.sort(key=lambda item: item[0])
            if any(
                current[0] < previous[1]
                for previous, current in zip(windows, windows[1:], strict=False)
            ):
                raise serializers.ValidationError(
                    {"working_hours": f"بازه‌های روز {day} نباید هم‌پوشانی داشته باشند."}
                )
            normalized[str(day)] = [item[2] for item in windows]
        return normalized


class StaffBranchSerializer(serializers.ModelSerializer):
    salon_name = serializers.CharField(source="salon.name", read_only=True)

    class Meta:
        model = Branch
        fields = ("id", "salon", "salon_name", "name", "is_active")
        read_only_fields = fields


class BranchClosureSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source="branch.name", read_only=True)

    class Meta:
        model = BranchClosure
        fields = ("id", "branch", "branch_name", "starts_at", "ends_at", "reason", "created_at")
        read_only_fields = ("id", "created_at")

    def validate(self, attrs):
        starts_at = attrs.get("starts_at", getattr(self.instance, "starts_at", None))
        ends_at = attrs.get("ends_at", getattr(self.instance, "ends_at", None))
        if starts_at and ends_at and starts_at >= ends_at:
            raise serializers.ValidationError("پایان تعطیلی باید پس از شروع آن باشد.")
        return attrs


class ServiceCategorySerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(source="parent.name", read_only=True)

    class Meta:
        model = ServiceCategory
        fields = ("id", "name", "slug", "parent", "parent_name", "icon", "sort_order")


class ServiceSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    salon_name = serializers.CharField(source="salon.name", read_only=True)

    class Meta:
        model = Service
        fields = (
            "id",
            "salon",
            "salon_name",
            "category",
            "category_name",
            "name",
            "description",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class BranchServiceSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source="service.name", read_only=True)
    category_name = serializers.CharField(source="service.category.name", read_only=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    price_type_label = serializers.CharField(source="get_price_type_display", read_only=True)

    class Meta:
        model = BranchService
        fields = (
            "id",
            "branch",
            "branch_name",
            "service",
            "service_name",
            "category_name",
            "price",
            "price_type",
            "price_type_label",
            "duration_minutes",
            "preparation_buffer_minutes",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate(self, attrs):
        branch = attrs.get("branch", getattr(self.instance, "branch", None))
        service = attrs.get("service", getattr(self.instance, "service", None))
        if branch and service and service.salon_id not in (None, branch.salon_id):
            raise serializers.ValidationError({"service": "این خدمت متعلق به سالن دیگری است."})
        return attrs


class StaffShiftSerializer(serializers.ModelSerializer):
    day_label = serializers.CharField(source="get_day_of_week_display", read_only=True)

    class Meta:
        model = StaffShift
        fields = ("id", "staff", "day_of_week", "day_label", "start_time", "end_time", "is_off")
        read_only_fields = ("id",)

    def validate(self, attrs):
        is_off = attrs.get("is_off", getattr(self.instance, "is_off", False))
        start = attrs.get("start_time", getattr(self.instance, "start_time", None))
        end = attrs.get("end_time", getattr(self.instance, "end_time", None))
        if not is_off and (start is None or end is None):
            raise serializers.ValidationError("برای روز کاری، ساعت شروع و پایان الزامی است.")
        if not is_off and start >= end:
            raise serializers.ValidationError("ساعت پایان باید پس از ساعت شروع باشد.")
        staff = attrs.get("staff", getattr(self.instance, "staff", None))
        day = attrs.get("day_of_week", getattr(self.instance, "day_of_week", None))
        if staff and not is_off:
            overlapping = StaffShift.objects.filter(
                staff=staff,
                day_of_week=day,
                is_off=False,
                start_time__lt=end,
                end_time__gt=start,
            )
            if self.instance:
                overlapping = overlapping.exclude(pk=self.instance.pk)
            if overlapping.exists():
                raise serializers.ValidationError(
                    "بازه کاری با بازه دیگری در همان روز هم‌پوشانی دارد."
                )
        return attrs


class StaffTimeOffSerializer(serializers.ModelSerializer):
    class Meta:
        model = StaffTimeOff
        fields = ("id", "staff", "starts_at", "ends_at", "reason", "created_at")
        read_only_fields = ("id", "created_at")

    def validate(self, attrs):
        if attrs["starts_at"] >= attrs["ends_at"]:
            raise serializers.ValidationError("پایان مرخصی باید پس از شروع آن باشد.")
        return attrs


class StaffServiceSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source="branch_service.service.name", read_only=True)
    base_duration_minutes = serializers.IntegerField(
        source="branch_service.duration_minutes", read_only=True
    )
    effective_duration_minutes = serializers.SerializerMethodField()

    class Meta:
        model = StaffService
        fields = (
            "id",
            "staff",
            "branch_service",
            "service_name",
            "base_duration_minutes",
            "duration_override_minutes",
            "effective_duration_minutes",
        )
        read_only_fields = ("id",)

    @staticmethod
    def get_effective_duration_minutes(obj) -> int:
        return obj.duration_override_minutes or obj.branch_service.duration_minutes

    def validate(self, attrs):
        staff = attrs.get("staff", getattr(self.instance, "staff", None))
        branch_service = attrs.get("branch_service", getattr(self.instance, "branch_service", None))
        if staff and branch_service and staff.branch_id != branch_service.branch_id:
            raise serializers.ValidationError("آرایشگر و خدمت باید متعلق به یک شعبه باشند.")
        return attrs


class StaffSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    shifts = StaffShiftSerializer(many=True, read_only=True)
    staff_services = StaffServiceSerializer(many=True, read_only=True)

    class Meta:
        model = Staff
        fields = (
            "id",
            "branch",
            "branch_name",
            "user",
            "first_name",
            "last_name",
            "full_name",
            "photo",
            "bio",
            "experience_years",
            "is_active",
            "shifts",
            "staff_services",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")
