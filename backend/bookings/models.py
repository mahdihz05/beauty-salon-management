from django.conf import settings
from django.db import models

from salons.models import Branch, BranchService, Staff


class Booking(models.Model):
    class Source(models.TextChoices):
        ONLINE = "online", "آنلاین"
        WALK_IN = "walk_in", "حضوری"

    class Status(models.TextChoices):
        PENDING_PAYMENT = "pending_payment", "در انتظار پرداخت"
        AWAITING_VERIFICATION = "awaiting_verification", "در انتظار تأیید واریز"
        CONFIRMED = "confirmed", "تأییدشده"
        COMPLETED = "completed", "انجام‌شده"
        CANCELLED = "cancelled", "لغوشده"
        NO_SHOW = "no_show", "عدم حضور"

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="bookings"
    )
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name="bookings")
    staff = models.ForeignKey(Staff, on_delete=models.PROTECT, related_name="bookings")
    status = models.CharField(
        max_length=24, choices=Status.choices, default=Status.PENDING_PAYMENT, db_index=True
    )
    source = models.CharField(
        max_length=12, choices=Source.choices, default=Source.ONLINE, db_index=True
    )
    start_at = models.DateTimeField(db_index=True)
    end_at = models.DateTimeField(db_index=True)
    total_price = models.PositiveBigIntegerField()
    deposit_amount = models.PositiveBigIntegerField(default=0)
    discount_code = models.ForeignKey(
        "DiscountCode",
        on_delete=models.PROTECT,
        related_name="bookings",
        null=True,
        blank=True,
    )
    discount_amount = models.PositiveBigIntegerField(default=0)
    notes = models.TextField(blank=True)
    hold_expires_at = models.DateTimeField(null=True, blank=True, db_index=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.CharField(max_length=500, blank=True)
    checked_in_at = models.DateTimeField(null=True, blank=True)
    checked_in_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="checked_in_bookings",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-start_at",)
        indexes = [
            models.Index(fields=("staff", "start_at", "end_at")),
            models.Index(fields=("branch", "status", "start_at")),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_at__gt=models.F("start_at")), name="booking_end_after_start"
            ),
            models.CheckConstraint(
                condition=models.Q(deposit_amount__lte=models.F("total_price")),
                name="booking_deposit_lte_total",
            ),
        ]
        verbose_name = "رزرو"
        verbose_name_plural = "رزروها"

    def __str__(self) -> str:
        return f"رزرو {self.pk} - {self.customer}"


class BookingItem(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="items")
    branch_service = models.ForeignKey(
        BranchService, on_delete=models.PROTECT, related_name="booking_items"
    )
    staff = models.ForeignKey(Staff, on_delete=models.PROTECT, related_name="booking_items")
    price = models.PositiveBigIntegerField()
    duration_minutes = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ("id",)
        verbose_name = "آیتم رزرو"
        verbose_name_plural = "آیتم‌های رزرو"

    def __str__(self) -> str:
        return f"{self.booking}: {self.branch_service.service}"


class DiscountCode(models.Model):
    class Type(models.TextChoices):
        PERCENT = "percent", "درصدی"
        FIXED = "fixed", "مبلغ ثابت"

    code = models.CharField(max_length=32, unique=True, db_index=True)
    salon = models.ForeignKey(
        "salons.Salon",
        on_delete=models.CASCADE,
        related_name="discount_codes",
        null=True,
        blank=True,
        help_text="کد بدون سالن، سراسری است.",
    )
    type = models.CharField(max_length=10, choices=Type.choices)
    value = models.PositiveBigIntegerField()
    minimum_purchase = models.PositiveBigIntegerField(default=0)
    maximum_discount = models.PositiveBigIntegerField(null=True, blank=True)
    usage_limit = models.PositiveIntegerField(null=True, blank=True)
    used_count = models.PositiveIntegerField(default=0)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.CheckConstraint(
                condition=models.Q(ends_at__gt=models.F("starts_at")),
                name="discount_ends_after_starts",
            )
        ]
        verbose_name = "کد تخفیف"
        verbose_name_plural = "کدهای تخفیف"

    def __str__(self) -> str:
        return self.code


class DiscountRedemption(models.Model):
    discount = models.ForeignKey(DiscountCode, on_delete=models.PROTECT, related_name="redemptions")
    booking = models.OneToOneField(
        Booking, on_delete=models.PROTECT, related_name="discount_redemption"
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="discount_redemptions"
    )
    amount = models.PositiveBigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "مصرف کد تخفیف"
        verbose_name_plural = "مصرف کدهای تخفیف"
