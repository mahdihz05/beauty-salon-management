from rest_framework import serializers

from .models import CustomerProfile, User
from .utils import normalize_iranian_phone


class CustomerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerProfile
        fields = ("email", "birth_date", "gender", "avatar")


class UserSerializer(serializers.ModelSerializer):
    profile = CustomerProfileSerializer(source="customer_profile", required=False)
    role_label = serializers.CharField(source="get_role_display", read_only=True)

    class Meta:
        model = User
        fields = ("id", "phone", "name", "role", "role_label", "profile", "created_at")
        read_only_fields = ("id", "phone", "role", "role_label", "created_at")

    def update(self, instance, validated_data):
        profile_data = validated_data.pop("customer_profile", {})
        instance = super().update(instance, validated_data)
        profile, _ = CustomerProfile.objects.get_or_create(user=instance)
        for field, value in profile_data.items():
            setattr(profile, field, value)
        profile.save()
        return instance


class OTPRequestSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=20)

    def validate_phone(self, value):
        return normalize_iranian_phone(value)


class OTPVerifySerializer(OTPRequestSerializer):
    code = serializers.RegexField(r"^\d{6}$", error_messages={"invalid": "کد باید ۶ رقمی باشد."})


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()
