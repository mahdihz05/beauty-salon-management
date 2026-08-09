from django.conf import settings
from django.db import models

from bookings.models import Booking


class Notification(models.Model):
    class Event(models.TextChoices):
        BOOKING_CONFIRMED = "booking_confirmed", "تأیید رزرو"
        BOOKING_REMINDER = "booking_reminder", "یادآوری رزرو"
        BOOKING_CANCELLED = "booking_cancelled", "لغو رزرو"

    class Channel(models.TextChoices):
        SMS = "sms", "پیامک"
        IN_APP = "in_app", "داخل برنامه"

    class Status(models.TextChoices):
        PENDING = "pending", "در انتظار"
        SENT = "sent", "ارسال‌شده"
        FAILED = "failed", "ناموفق"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="notifications"
    )
    booking = models.ForeignKey(Booking, on_delete=models.PROTECT, related_name="notifications")
    event = models.CharField(max_length=24, choices=Event.choices)
    channel = models.CharField(max_length=10, choices=Channel.choices, default=Channel.SMS)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    message = models.CharField(max_length=500)
    provider_ref = models.CharField(max_length=120, blank=True)
    error = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("recipient", "booking", "event", "channel"),
                name="unique_booking_event_notification",
            )
        ]
        verbose_name = "اعلان"
        verbose_name_plural = "اعلان‌ها"
