from django.db import transaction
from django.db.models import F
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import Booking, DiscountCode, DiscountRedemption


def calculate_discount(discount: DiscountCode, subtotal: int) -> int:
    if discount.type == DiscountCode.Type.PERCENT:
        amount = subtotal * discount.value // 100
    else:
        amount = discount.value
    if discount.maximum_discount is not None:
        amount = min(amount, discount.maximum_discount)
    return min(amount, subtotal)


@transaction.atomic
def apply_discount_to_booking(*, booking: Booking, raw_code: str) -> Booking:
    booking = Booking.objects.select_for_update().get(pk=booking.pk)
    code = raw_code.strip().upper()
    if not code:
        return booking
    discount = DiscountCode.objects.select_for_update().filter(code__iexact=code).first()
    now = timezone.now()
    if not discount or not discount.is_active or not (discount.starts_at <= now < discount.ends_at):
        raise ValidationError("کد تخفیف معتبر یا فعال نیست.")
    if discount.salon_id and discount.salon_id != booking.branch.salon_id:
        raise ValidationError("این کد برای سالن انتخاب‌شده معتبر نیست.")
    if discount.usage_limit is not None and discount.used_count >= discount.usage_limit:
        raise ValidationError("ظرفیت استفاده از این کد تخفیف تمام شده است.")
    subtotal = sum(item.price for item in booking.items.all())
    if subtotal < discount.minimum_purchase:
        raise ValidationError("مبلغ رزرو کمتر از حداقل خرید این کد است.")
    amount = calculate_discount(discount, subtotal)
    booking.discount_code = discount
    booking.discount_amount = amount
    booking.total_price = subtotal - amount
    booking.deposit_amount = booking.total_price * booking.branch.deposit_percent // 100
    booking.save(
        update_fields=(
            "discount_code",
            "discount_amount",
            "total_price",
            "deposit_amount",
            "updated_at",
        )
    )
    return booking


@transaction.atomic
def redeem_booking_discount(booking: Booking) -> None:
    if not booking.discount_code_id:
        return
    if DiscountRedemption.objects.filter(booking=booking).exists():
        return
    discount = DiscountCode.objects.select_for_update().get(pk=booking.discount_code_id)
    if discount.usage_limit is not None and discount.used_count >= discount.usage_limit:
        raise ValidationError("ظرفیت کد تخفیف پیش از پرداخت تکمیل شد.")
    DiscountRedemption.objects.create(
        discount=discount,
        booking=booking,
        customer=booking.customer,
        amount=booking.discount_amount,
    )
    DiscountCode.objects.filter(pk=discount.pk).update(used_count=F("used_count") + 1)
