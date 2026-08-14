from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError

from bookings.discounts import apply_discount_to_booking, redeem_booking_discount
from bookings.models import Booking

from .models import Payment, Settlement, Wallet, WalletTransaction
from .providers import get_payment_provider


def _locked_wallet(user) -> Wallet:
    wallet, _ = Wallet.objects.get_or_create(user=user)
    return Wallet.objects.select_for_update().get(pk=wallet.pk)


@transaction.atomic
def submit_manual_payment(
    *,
    customer,
    booking_id: int,
    payment_type: str,
    method: str,
    tracking_code: str = "",
    receipt=None,
    discount_code: str = "",
) -> Payment:
    try:
        booking = (
            Booking.objects.select_for_update().select_related("branch__salon").get(pk=booking_id)
        )
    except Booking.DoesNotExist as exc:
        raise NotFound("رزرو پیدا نشد.") from exc
    if booking.customer_id != customer.id:
        raise ValidationError("این رزرو متعلق به شما نیست.")
    if booking.status != Booking.Status.PENDING_PAYMENT:
        raise ValidationError("این رزرو در انتظار انتخاب روش پرداخت نیست.")
    if booking.hold_expires_at and booking.hold_expires_at <= timezone.now():
        raise ValidationError("مهلت ده‌دقیقه‌ای پرداخت تمام شده است.")
    if method not in (Payment.Method.IN_PERSON, Payment.Method.CARD_TO_CARD):
        raise ValidationError("روش پرداخت معتبر نیست.")
    if method == Payment.Method.CARD_TO_CARD and not (tracking_code or receipt):
        raise ValidationError("تصویر رسید یا کد پیگیری الزامی است.")
    if discount_code:
        booking = apply_discount_to_booking(booking=booking, raw_code=discount_code)
    amount = booking.deposit_amount if payment_type == Payment.Type.DEPOSIT else booking.total_price
    if amount <= 0:
        raise ValidationError("مبلغ پرداخت باید بیشتر از صفر باشد.")
    Payment.objects.filter(booking=booking, status=Payment.Status.PENDING).update(
        status=Payment.Status.FAILED
    )
    payment = Payment.objects.create(
        booking=booking,
        amount=amount,
        type=payment_type,
        method=method,
        provider="manual",
        tracking_code=tracking_code,
        receipt=receipt,
    )
    booking.hold_expires_at = None
    if method == Payment.Method.IN_PERSON:
        booking.status = Booking.Status.CONFIRMED
        redeem_booking_discount(booking)
    else:
        booking.status = Booking.Status.AWAITING_VERIFICATION
    booking.save(update_fields=("status", "hold_expires_at", "updated_at"))
    if method == Payment.Method.IN_PERSON:
        from notifications.models import Notification
        from notifications.services import send_booking_notification

        send_booking_notification(booking=booking, event=Notification.Event.BOOKING_CONFIRMED)
    return payment


@transaction.atomic
def verify_card_transfer(*, payment_id: int, verifier, next_status: str) -> Payment:
    try:
        payment = (
            Payment.objects.select_for_update()
            .select_related("booking__branch")
            .get(pk=payment_id, method=Payment.Method.CARD_TO_CARD)
        )
    except Payment.DoesNotExist as exc:
        raise NotFound("پرداخت کارت‌به‌کارت پیدا نشد.") from exc
    if payment.status != Payment.Status.PENDING:
        raise ValidationError("این پرداخت قبلاً بررسی شده است.")
    booking = Booking.objects.select_for_update().get(pk=payment.booking_id)
    payment.status = next_status
    payment.verified_by = verifier
    payment.verified_at = timezone.now()
    if next_status == Payment.Status.PAID:
        payment.paid_at = payment.verified_at
        booking.status = Booking.Status.CONFIRMED
        redeem_booking_discount(booking)
    else:
        booking.status = Booking.Status.CANCELLED
        booking.cancelled_at = timezone.now()
        booking.cancellation_reason = "رد رسید کارت‌به‌کارت"
    payment.save(update_fields=("status", "verified_by", "verified_at", "paid_at", "updated_at"))
    booking.save(update_fields=("status", "cancelled_at", "cancellation_reason", "updated_at"))
    from notifications.models import Notification
    from notifications.services import send_booking_notification

    send_booking_notification(
        booking=booking,
        event=(
            Notification.Event.BOOKING_CONFIRMED
            if next_status == Payment.Status.PAID
            else Notification.Event.BOOKING_CANCELLED
        ),
    )
    return payment


@transaction.atomic
def start_payment(
    *, customer, booking_id: int, payment_type: str, callback_url: str, discount_code: str = ""
) -> Payment:
    try:
        booking = (
            Booking.objects.select_for_update().select_related("branch__salon").get(pk=booking_id)
        )
    except Booking.DoesNotExist as exc:
        raise NotFound("رزرو پیدا نشد.") from exc
    if booking.customer_id != customer.id:
        raise ValidationError("این رزرو متعلق به شما نیست.")
    if booking.status != Booking.Status.PENDING_PAYMENT:
        raise ValidationError("این رزرو در انتظار پرداخت نیست.")
    if booking.hold_expires_at and booking.hold_expires_at <= timezone.now():
        raise ValidationError("مهلت پرداخت این رزرو تمام شده است.")
    if payment_type not in (Payment.Type.DEPOSIT, Payment.Type.FULL):
        raise ValidationError("نوع پرداخت معتبر نیست.")
    if discount_code:
        booking = apply_discount_to_booking(booking=booking, raw_code=discount_code)
    amount = booking.deposit_amount if payment_type == Payment.Type.DEPOSIT else booking.total_price
    if amount <= 0:
        raise ValidationError("مبلغ پرداخت باید بیشتر از صفر باشد.")

    existing = Payment.objects.filter(
        booking=booking,
        type=payment_type,
        amount=amount,
        status=Payment.Status.PENDING,
    ).first()
    if existing:
        return existing
    Payment.objects.filter(booking=booking, status=Payment.Status.PENDING).update(
        status=Payment.Status.FAILED
    )

    provider = get_payment_provider(getattr(settings, "PAYMENT_PROVIDER", "mock"))
    payment = Payment.objects.create(
        booking=booking,
        amount=amount,
        type=payment_type,
        provider=provider.name,
    )
    resolved_callback_url = callback_url.format(payment_id=payment.pk)
    gateway_request = provider.request(
        amount=amount,
        callback_url=resolved_callback_url,
        description=f"رزرو شماره {booking.pk}",
    )
    payment.gateway_ref = gateway_request.authority
    payment.provider_data = {
        **gateway_request.provider_data,
        "redirect_url": gateway_request.redirect_url,
        "callback_url": resolved_callback_url,
    }
    payment.save(update_fields=("gateway_ref", "provider_data", "updated_at"))
    return payment


@transaction.atomic
def confirm_payment(*, customer=None, payment_id: int) -> Payment:
    try:
        payment = Payment.objects.select_for_update().select_related("booking").get(pk=payment_id)
    except Payment.DoesNotExist as exc:
        raise NotFound("پرداخت پیدا نشد.") from exc
    if customer is not None and payment.booking.customer_id != customer.id:
        raise ValidationError("این پرداخت متعلق به شما نیست.")
    if payment.status == Payment.Status.PAID:
        return payment
    if payment.status != Payment.Status.PENDING:
        raise ValidationError("این پرداخت قابل تأیید نیست.")

    booking = Booking.objects.select_for_update().get(pk=payment.booking_id)
    if booking.status != Booking.Status.PENDING_PAYMENT:
        raise ValidationError("وضعیت رزرو برای تأیید پرداخت معتبر نیست.")
    if booking.hold_expires_at and booking.hold_expires_at <= timezone.now():
        raise ValidationError("مهلت پرداخت این رزرو تمام شده است.")

    verification = get_payment_provider(payment.provider).verify(
        authority=payment.gateway_ref, amount=payment.amount
    )
    if not verification.successful:
        payment.status = Payment.Status.FAILED
        payment.save(update_fields=("status", "updated_at"))
        raise ValidationError("پرداخت توسط درگاه تأیید نشد.")

    payment.status = Payment.Status.PAID
    payment.paid_at = timezone.now()
    payment.provider_data = {**payment.provider_data, **verification.provider_data}
    payment.gateway_ref = verification.reference
    payment.save(update_fields=("status", "paid_at", "provider_data", "gateway_ref", "updated_at"))
    booking.status = Booking.Status.CONFIRMED
    booking.hold_expires_at = None
    redeem_booking_discount(booking)
    booking.save(update_fields=("status", "hold_expires_at", "updated_at"))
    from notifications.models import Notification
    from notifications.services import send_booking_notification

    send_booking_notification(booking=booking, event=Notification.Event.BOOKING_CONFIRMED)
    return payment


@transaction.atomic
def record_remainder_payment(*, booking_id: int, method: str) -> Payment:
    try:
        booking = Booking.objects.select_for_update().get(pk=booking_id)
    except Booking.DoesNotExist as exc:
        raise NotFound("رزرو پیدا نشد.") from exc
    if booking.status != Booking.Status.CONFIRMED:
        raise ValidationError("مانده فقط برای رزرو تأییدشده قابل ثبت است.")
    if method != Payment.Method.IN_PERSON:
        raise ValidationError("در نسخه فعلی مانده حضوری فقط به‌صورت نقدی ثبت می‌شود.")

    paid_total = (
        Payment.objects.filter(booking=booking, status=Payment.Status.PAID).aggregate(
            total=Sum("amount")
        )["total"]
        or 0
    )
    remainder = booking.total_price - paid_total
    if remainder <= 0:
        raise ValidationError("این رزرو مانده پرداخت‌نشده ندارد.")
    Payment.objects.filter(
        booking=booking,
        status=Payment.Status.PENDING,
        method=Payment.Method.IN_PERSON,
    ).update(status=Payment.Status.FAILED)
    return Payment.objects.create(
        booking=booking,
        amount=remainder,
        type=Payment.Type.REMAINDER,
        status=Payment.Status.PAID,
        method=Payment.Method.IN_PERSON,
        provider="manual",
        gateway_ref=f"in-person-booking-{booking.pk}",
        paid_at=timezone.now(),
    )


@transaction.atomic
def cancel_booking_with_policy(*, booking_id: int, reason: str, now=None) -> tuple[Booking, int]:
    booking = Booking.objects.select_for_update().get(pk=booking_id)
    if booking.status not in (
        Booking.Status.PENDING_PAYMENT,
        Booking.Status.AWAITING_VERIFICATION,
        Booking.Status.CONFIRMED,
    ):
        raise ValidationError("این رزرو قابل لغو نیست.")

    refund_amount = 0
    free_hours = int(getattr(settings, "CANCELLATION_FREE_HOURS", 24))
    now = now or timezone.now()
    eligible = booking.start_at - now >= timedelta(hours=free_hours)
    if not eligible:
        raise ValidationError("لغو نوبت فقط تا ۲۴ ساعت پیش از زمان شروع امکان‌پذیر است.")
    paid = list(
        Payment.objects.select_for_update().filter(booking=booking, status=Payment.Status.PAID)
    )
    if eligible and paid:
        refund_amount = sum(payment.amount for payment in paid)
        wallet = _locked_wallet(booking.customer)
        WalletTransaction.objects.create(
            wallet=wallet,
            amount=refund_amount,
            type=WalletTransaction.Type.REFUND,
            related_booking=booking,
            salon=booking.branch.salon,
            description=f"بازپرداخت لغو رزرو {booking.pk}",
        )
        wallet.balance += refund_amount
        wallet.save(update_fields=("balance", "updated_at"))
        Payment.objects.filter(pk__in=[payment.pk for payment in paid]).update(
            status=Payment.Status.REFUNDED
        )

    booking.status = Booking.Status.CANCELLED
    booking.cancelled_at = now
    booking.cancellation_reason = reason[:500]
    booking.save(update_fields=("status", "cancelled_at", "cancellation_reason", "updated_at"))
    from notifications.models import Notification
    from notifications.services import send_booking_notification

    send_booking_notification(booking=booking, event=Notification.Event.BOOKING_CANCELLED)
    return booking, refund_amount


@transaction.atomic
def credit_salon_for_booking(*, booking_id: int) -> int:
    booking = (
        Booking.objects.select_for_update()
        .select_related("branch__salon__owner")
        .get(pk=booking_id)
    )
    if booking.status not in (Booking.Status.COMPLETED, Booking.Status.NO_SHOW):
        raise ValidationError("درآمد فقط برای نوبت انجام‌شده یا عدم حضور ثبت می‌شود.")
    gross = (
        Payment.objects.filter(booking=booking, status=Payment.Status.PAID).aggregate(
            total=Sum("amount")
        )["total"]
        or 0
    )
    if gross <= 0:
        return 0
    wallet = _locked_wallet(booking.branch.salon.owner)
    if WalletTransaction.objects.filter(
        wallet=wallet,
        related_booking=booking,
        type=WalletTransaction.Type.SALON_EARNING,
    ).exists():
        return 0
    commission = gross * int(getattr(settings, "PLATFORM_COMMISSION_PERCENT", 10)) // 100
    WalletTransaction.objects.create(
        wallet=wallet,
        amount=gross,
        type=WalletTransaction.Type.SALON_EARNING,
        related_booking=booking,
        salon=booking.branch.salon,
        description=f"درآمد رزرو {booking.pk}",
    )
    if commission:
        WalletTransaction.objects.create(
            wallet=wallet,
            amount=-commission,
            type=WalletTransaction.Type.COMMISSION,
            related_booking=booking,
            salon=booking.branch.salon,
            description=f"کارمزد سامانه برای رزرو {booking.pk}",
        )
    wallet.balance += gross - commission
    wallet.save(update_fields=("balance", "updated_at"))
    return gross - commission


@transaction.atomic
def request_settlement(*, user, salon, amount: int, bank_account: str) -> Settlement:
    if amount <= 0:
        raise ValidationError("مبلغ تسویه باید بیشتر از صفر باشد.")
    wallet = _locked_wallet(user)
    salon_balance = (
        WalletTransaction.objects.filter(wallet=wallet, salon=salon).aggregate(total=Sum("amount"))[
            "total"
        ]
        or 0
    )
    has_scoped_transactions = WalletTransaction.objects.filter(
        wallet=wallet, salon__isnull=False
    ).exists()
    if salon_balance == 0 and not has_scoped_transactions:
        salon_balance = wallet.balance
    if salon_balance < amount:
        raise ValidationError("مانده قابل تسویه این سالن کافی نیست.")
    settlement = Settlement.objects.create(
        wallet=wallet, salon=salon, amount=amount, bank_account=bank_account
    )
    WalletTransaction.objects.create(
        wallet=wallet,
        amount=-amount,
        type=WalletTransaction.Type.SETTLEMENT,
        salon=salon,
        description=f"رزرو موجودی برای تسویه {settlement.pk}",
    )
    wallet.balance -= amount
    wallet.save(update_fields=("balance", "updated_at"))
    return settlement


@transaction.atomic
def process_settlement(*, settlement_id: int, next_status: str, note: str = "") -> Settlement:
    try:
        settlement = (
            Settlement.objects.select_for_update().select_related("wallet").get(pk=settlement_id)
        )
    except Settlement.DoesNotExist as exc:
        raise NotFound("درخواست تسویه پیدا نشد.") from exc
    if settlement.status != Settlement.Status.REQUESTED:
        raise ValidationError("این درخواست قبلاً پردازش شده است.")
    if next_status not in (Settlement.Status.PAID, Settlement.Status.REJECTED):
        raise ValidationError("وضعیت تسویه معتبر نیست.")
    if next_status == Settlement.Status.REJECTED:
        wallet = Wallet.objects.select_for_update().get(pk=settlement.wallet_id)
        wallet.balance += settlement.amount
        wallet.save(update_fields=("balance", "updated_at"))
        WalletTransaction.objects.create(
            wallet=wallet,
            amount=settlement.amount,
            type=WalletTransaction.Type.ADJUSTMENT,
            salon=settlement.salon,
            description=f"بازگشت مبلغ تسویه ردشده {settlement.pk}",
        )
    settlement.status = next_status
    settlement.note = note[:500]
    settlement.processed_at = timezone.now()
    settlement.save(update_fields=("status", "note", "processed_at"))
    return settlement
