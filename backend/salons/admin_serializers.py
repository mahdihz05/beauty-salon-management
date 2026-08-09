from rest_framework import serializers

from .models import City, District, ServiceCategory


class AdminCitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ("id", "name", "slug", "is_active")
        read_only_fields = ("id",)


class AdminDistrictSerializer(serializers.ModelSerializer):
    city_name = serializers.CharField(source="city.name", read_only=True)

    class Meta:
        model = District
        fields = ("id", "city", "city_name", "name", "slug", "is_active")
        read_only_fields = ("id",)


class AdminCategorySerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(source="parent.name", read_only=True)

    class Meta:
        model = ServiceCategory
        fields = (
            "id",
            "name",
            "slug",
            "parent",
            "parent_name",
            "icon",
            "is_active",
            "sort_order",
        )
        read_only_fields = ("id",)


class RejectionSerializer(serializers.Serializer):
    reason = serializers.CharField(min_length=5, max_length=1000)


class AdminDashboardSerializer(serializers.Serializer):
    users = serializers.IntegerField()
    salons = serializers.IntegerField()
    pending_salons = serializers.IntegerField()
    approved_salons = serializers.IntegerField()
    branches = serializers.IntegerField()
    services = serializers.IntegerField()
