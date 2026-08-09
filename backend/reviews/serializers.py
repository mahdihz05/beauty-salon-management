from rest_framework import serializers

from bookings.models import Booking

from .models import Review, ReviewImage


class ReviewImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewImage
        fields = ("id", "image")


class ReviewSerializer(serializers.ModelSerializer):
    images = ReviewImageSerializer(many=True, read_only=True)
    uploaded_images = serializers.ListField(
        child=serializers.ImageField(), required=False, write_only=True, max_length=5
    )
    customer_name = serializers.SerializerMethodField()
    salon_name = serializers.CharField(source="salon.name", read_only=True)
    staff_name = serializers.CharField(source="staff.full_name", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Review
        fields = (
            "id",
            "booking",
            "customer_name",
            "salon",
            "salon_name",
            "staff",
            "staff_name",
            "overall_rating",
            "quality_rating",
            "cleanliness_rating",
            "behavior_rating",
            "value_rating",
            "comment",
            "status",
            "status_label",
            "images",
            "uploaded_images",
            "created_at",
        )
        read_only_fields = (
            "id",
            "customer_name",
            "salon",
            "salon_name",
            "staff",
            "staff_name",
            "status",
            "status_label",
            "images",
            "created_at",
        )

    def get_customer_name(self, obj) -> str:
        return obj.customer.name or "کاربر نوبت‌آرا"

    def validate_booking(self, booking):
        request = self.context["request"]
        if booking.customer_id != request.user.id:
            raise serializers.ValidationError("این رزرو متعلق به شما نیست.")
        if booking.status != Booking.Status.COMPLETED:
            raise serializers.ValidationError("ثبت نظر فقط برای نوبت انجام‌شده امکان‌پذیر است.")
        if Review.objects.filter(booking=booking).exists():
            raise serializers.ValidationError("برای این رزرو قبلاً نظر ثبت شده است.")
        return booking

    def create(self, validated_data):
        uploaded_images = validated_data.pop("uploaded_images", [])
        booking = validated_data["booking"]
        review = Review.objects.create(
            **validated_data,
            customer=self.context["request"].user,
            salon=booking.branch.salon,
            staff=booking.staff,
        )
        ReviewImage.objects.bulk_create(
            [ReviewImage(review=review, image=image) for image in uploaded_images]
        )
        return review


class ReviewModerationSerializer(serializers.ModelSerializer):
    status = serializers.ChoiceField(choices=Review.Status.choices)

    class Meta:
        model = Review
        fields = ("status",)
