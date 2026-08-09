import secrets
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import Throttled, ValidationError

from core.audit import get_client_ip

from .models import CustomerProfile, OTPChallenge, User
from .providers import get_sms_provider
from .utils import normalize_iranian_phone


@dataclass(frozen=True)
class OTPDispatch:
    challenge: OTPChallenge
    debug_code: str | None


def request_otp(*, phone: str, request) -> OTPDispatch:
    phone = normalize_iranian_phone(phone)
    since = timezone.now() - timedelta(hours=1)
    request_count = OTPChallenge.objects.filter(phone=phone, created_at__gte=since).count()
    if request_count >= settings.OTP_REQUEST_LIMIT_PER_HOUR:
        raise Throttled(detail="تعداد درخواست‌ها بیش از حد مجاز است؛ کمی بعد تلاش کنید.")

    code = f"{secrets.randbelow(1_000_000):06d}"
    challenge = OTPChallenge.objects.create(
        phone=phone,
        code_hash=make_password(code),
        expires_at=timezone.now() + timedelta(seconds=settings.OTP_CODE_TTL_SECONDS),
        request_ip=get_client_ip(request),
    )
    get_sms_provider(settings.OTP_PROVIDER).send_otp(phone, code)
    return OTPDispatch(challenge=challenge, debug_code=code if settings.DEBUG else None)


def verify_otp(*, phone: str, code: str) -> tuple[User, bool]:
    phone = normalize_iranian_phone(phone)
    invalid_code = False
    with transaction.atomic():
        challenge = (
            OTPChallenge.objects.select_for_update()
            .filter(phone=phone, purpose=OTPChallenge.Purpose.LOGIN, consumed_at__isnull=True)
            .order_by("-created_at")
            .first()
        )
        if challenge is None:
            raise ValidationError("کد فعالی برای این شماره وجود ندارد.")
        if challenge.expires_at <= timezone.now():
            raise ValidationError("کد منقضی شده است؛ کد جدید دریافت کنید.")
        if challenge.attempts >= challenge.max_attempts:
            raise ValidationError("تعداد تلاش‌های ناموفق بیش از حد مجاز است.")
        if not check_password(code, challenge.code_hash):
            challenge.attempts += 1
            challenge.save(update_fields=("attempts",))
            invalid_code = True
        else:
            challenge.consumed_at = timezone.now()
            challenge.save(update_fields=("consumed_at",))
            user, created = User.objects.get_or_create(phone=phone)
            CustomerProfile.objects.get_or_create(user=user)
            if user.phone_verified_at is None:
                user.phone_verified_at = timezone.now()
                user.save(update_fields=("phone_verified_at",))
    if invalid_code:
        raise ValidationError("کد واردشده صحیح نیست.")
    return user, created
