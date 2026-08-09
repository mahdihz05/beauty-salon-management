from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from bookings.models import Booking
from core.validators import validate_image_size
from salons.models import Salon, Staff


class Review(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "در انتظار بررسی"
        PUBLISHED = "published", "منتشرشده"
        HIDDEN = "hidden", "مخفی"

    booking = models.OneToOneField(Booking, on_delete=models.PROTECT, related_name="review")
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="reviews"
    )
    salon = models.ForeignKey(Salon, on_delete=models.CASCADE, related_name="reviews")
    staff = models.ForeignKey(
        Staff,
        on_delete=models.PROTECT,
        related_name="reviews",
        null=True,
        blank=True,
    )
    overall_rating = models.PositiveSmallIntegerField(
        validators=(MinValueValidator(1), MaxValueValidator(5))
    )
    quality_rating = models.PositiveSmallIntegerField(
        validators=(MinValueValidator(1), MaxValueValidator(5))
    )
    cleanliness_rating = models.PositiveSmallIntegerField(
        validators=(MinValueValidator(1), MaxValueValidator(5))
    )
    behavior_rating = models.PositiveSmallIntegerField(
        validators=(MinValueValidator(1), MaxValueValidator(5))
    )
    value_rating = models.PositiveSmallIntegerField(
        validators=(MinValueValidator(1), MaxValueValidator(5)), default=5
    )
    comment = models.TextField(max_length=2000)
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "نظر"
        verbose_name_plural = "نظرات"

    def __str__(self) -> str:
        return f"نظر رزرو {self.booking_id}"


class ReviewImage(models.Model):
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="reviews/%Y/%m/", validators=(validate_image_size,))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("id",)
        verbose_name = "تصویر نظر"
        verbose_name_plural = "تصاویر نظر"
