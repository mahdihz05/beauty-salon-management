from rest_framework import serializers

from accounts.models import FavoriteSalon

from .models import Branch, BranchService, Salon, SalonImage, ServiceCategory, Staff


class PublicCategorySerializer(serializers.ModelSerializer):
    service_count = serializers.IntegerField(read_only=True)
    salon_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = ServiceCategory
        fields = ("id", "name", "slug", "icon", "service_count", "salon_count")


class PublicSalonImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalonImage
        fields = ("id", "image", "alt_text", "is_cover")


class PublicStaffSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = Staff
        fields = ("id", "full_name", "photo", "bio", "experience_years")


class PublicBranchServiceSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source="service.name", read_only=True)
    description = serializers.CharField(source="service.description", read_only=True)
    category_id = serializers.IntegerField(source="service.category_id", read_only=True)
    category_name = serializers.CharField(source="service.category.name", read_only=True)
    price_type_label = serializers.CharField(source="get_price_type_display", read_only=True)

    class Meta:
        model = BranchService
        fields = (
            "id",
            "service_name",
            "description",
            "category_id",
            "category_name",
            "price",
            "price_type",
            "price_type_label",
            "duration_minutes",
        )


class PublicBranchSerializer(serializers.ModelSerializer):
    city_name = serializers.CharField(source="city.name", read_only=True)
    district_name = serializers.CharField(source="district.name", read_only=True)
    services = PublicBranchServiceSerializer(source="branch_services", many=True, read_only=True)
    staff = PublicStaffSerializer(many=True, read_only=True)

    class Meta:
        model = Branch
        fields = (
            "id",
            "name",
            "city_name",
            "district_name",
            "address",
            "latitude",
            "longitude",
            "phone",
            "working_hours",
            "amenities",
            "services",
            "staff",
        )


class PublicSalonListSerializer(serializers.ModelSerializer):
    type_label = serializers.CharField(source="get_type_display", read_only=True)
    city = serializers.SerializerMethodField()
    district = serializers.SerializerMethodField()
    cover_image = serializers.SerializerMethodField()
    is_favorite = serializers.SerializerMethodField()

    class Meta:
        model = Salon
        fields = (
            "id",
            "name",
            "slug",
            "type",
            "type_label",
            "description",
            "rating_average",
            "review_count",
            "is_featured",
            "city",
            "district",
            "cover_image",
            "is_favorite",
        )

    def get_city(self, obj) -> str:
        branch = next(iter(obj.branches.all()), None)
        return branch.city.name if branch else ""

    def get_district(self, obj) -> str:
        branch = next(iter(obj.branches.all()), None)
        return branch.district.name if branch and branch.district else ""

    def get_cover_image(self, obj) -> str | None:
        image = next((item for item in obj.images.all() if item.is_cover), None)
        image = image or next(iter(obj.images.all()), None)
        if not image:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(image.image.url) if request else image.image.url

    def get_is_favorite(self, obj) -> bool:
        request = self.context.get("request")
        annotated = getattr(obj, "_is_favorite", None)
        if annotated is not None:
            return bool(annotated)
        return bool(
            request
            and request.user.is_authenticated
            and obj.favorited_by.filter(user=request.user).exists()
        )


class PublicSalonDetailSerializer(PublicSalonListSerializer):
    min_price = serializers.SerializerMethodField()
    images = PublicSalonImageSerializer(many=True, read_only=True)
    branches = PublicBranchSerializer(many=True, read_only=True)

    class Meta(PublicSalonListSerializer.Meta):
        fields = PublicSalonListSerializer.Meta.fields + ("min_price", "images", "branches")

    @staticmethod
    def get_min_price(obj) -> int | None:
        prices = [
            service.price
            for branch in obj.branches.all()
            for service in branch.branch_services.all()
            if service.is_active
        ]
        return min(prices) if prices else None


class FavoriteSalonSerializer(serializers.ModelSerializer):
    salon = serializers.PrimaryKeyRelatedField(
        queryset=Salon.objects.filter(status=Salon.Status.APPROVED)
    )
    salon_details = PublicSalonListSerializer(source="salon", read_only=True)

    class Meta:
        model = FavoriteSalon
        fields = ("id", "salon", "salon_details", "created_at")
        read_only_fields = ("id", "created_at")

    def validate_salon(self, salon):
        request = self.context["request"]
        if FavoriteSalon.objects.filter(user=request.user, salon=salon).exists():
            raise serializers.ValidationError("این سالن قبلاً به علاقه‌مندی‌ها اضافه شده است.")
        return salon
