from django.conf import settings
from django.db import models

from bookings.models import Booking


class Payment(models.Model):
    class Type(models.TextChoices):
        DEPOSIT = "deposit", "بیعانه"
        FULL = "full", "پرداخت کامل"
        REMAINDER = "remainder", "مانده"

    class Status(models.TextChoices):
        PENDING = "pending", "در انتظار"
        PAID = "paid", "پرداخت‌شده"
        FAILED = "failed", "ناموفق"
        REFUNDED = "refunded", "بازپرداخت‌شده"

    class Method(models.TextChoices):
        IN_PERSON = "in_person", "حضوری"
        CARD_TO_CARD = "card_to_card", "کارت‌به‌کارت"
        # Legacy values are intentionally retained for historical records.
        ONLINE = "online", "آنلاین"
        CASH = "cash", "نقدی"
        WALLET = "wallet", "کیف پول"

    booking = models.ForeignKey(Booking, on_delete=models.PROTECT, related_name="payments")
    amount = models.PositiveBigIntegerField()
    type = models.CharField(max_length=12, choices=Type.choices)
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    method = models.CharField(max_length=16, choices=Method.choices, default=Method.IN_PERSON)
    gateway_ref = models.CharField(max_length=120, blank=True, db_index=True)
    provider = models.CharField(max_length=40, default="mock")
    provider_data = models.JSONField(default=dict, blank=True)
    receipt = models.ImageField(upload_to="payments/receipts/", blank=True)
    tracking_code = models.CharField(max_length=80, blank=True, db_index=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="verified_payments",
        null=True,
        blank=True,
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "پرداخت"
        verbose_name_plural = "پرداخت‌ها"

    def __str__(self) -> str:
        return f"پرداخت {self.pk} - {self.amount}"


class Wallet(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wallet"
    )
    balance = models.BigIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "کیف پول"
        verbose_name_plural = "کیف پول‌ها"

    def __str__(self) -> str:
        return f"کیف پول {self.user}"


class WalletTransaction(models.Model):
    class Type(models.TextChoices):
        REFUND = "refund", "بازپرداخت"
        SALON_EARNING = "salon_earning", "درآمد سالن"
        COMMISSION = "commission", "کارمزد سامانه"
        SETTLEMENT = "settlement", "تسویه"
        ADJUSTMENT = "adjustment", "اصلاح دستی"

    wallet = models.ForeignKey(Wallet, on_delete=models.PROTECT, related_name="transactions")
    amount = models.BigIntegerField(help_text="مبلغ مثبت برای بستانکار و منفی برای بدهکار")
    type = models.CharField(max_length=20, choices=Type.choices)
    related_booking = models.ForeignKey(
        Booking,
        on_delete=models.PROTECT,
        related_name="wallet_transactions",
        null=True,
        blank=True,
    )
    salon = models.ForeignKey(
        "salons.Salon",
        on_delete=models.PROTECT,
        related_name="wallet_transactions",
        null=True,
        blank=True,
    )
    description = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("wallet", "related_booking", "type"),
                condition=models.Q(related_booking__isnull=False),
                name="unique_wallet_booking_transaction_type",
            )
        ]
        verbose_name = "تراکنش کیف پول"
        verbose_name_plural = "تراکنش‌های کیف پول"

    def __str__(self) -> str:
        return f"{self.wallet}: {self.amount}"


class Settlement(models.Model):
    class Status(models.TextChoices):
        REQUESTED = "requested", "درخواست‌شده"
        PAID = "paid", "واریزشده"
        REJECTED = "rejected", "ردشده"

    wallet = models.ForeignKey(Wallet, on_delete=models.PROTECT, related_name="settlements")
    salon = models.ForeignKey(
        "salons.Salon",
        on_delete=models.PROTECT,
        related_name="settlements",
        null=True,
        blank=True,
    )
    amount = models.PositiveBigIntegerField()
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.REQUESTED, db_index=True
    )
    bank_account = models.CharField(max_length=40)
    note = models.CharField(max_length=500, blank=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-requested_at",)
        verbose_name = "تسویه"
        verbose_name_plural = "تسویه‌ها"

    def __str__(self) -> str:
        return f"تسویه {self.pk} - {self.amount}"
