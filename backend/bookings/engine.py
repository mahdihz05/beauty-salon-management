from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from salons.models import Branch, BranchService, Staff, StaffService, StaffShift, StaffTimeOff

from .models import Booking, BookingItem

HOLD_MINUTES = 10


@dataclass(frozen=True)
class AvailableSlot:
    start_at: datetime
    end_at: datetime
    staff_id: int
    staff_name: str
    total_price: int
    duration_minutes: int


def expire_stale_holds(now: datetime | None = None) -> int:
    now = now or timezone.now()
    return Booking.objects.filter(
        status=Booking.Status.PENDING_PAYMENT, hold_expires_at__lte=now
    ).update(
        status=Booking.Status.CANCELLED,
        cancelled_at=now,
        cancellation_reason="انقضای مهلت پرداخت",
    )


def _day_of_week(target_date: date) -> int:
    return (target_date.weekday() + 2) % 7


def _ceil_to_grid(value: datetime, minutes: int) -> datetime:
    discarded = timedelta(
        minutes=value.minute % minutes,
        seconds=value.second,
        microseconds=value.microsecond,
    )
    value -= discarded
    return value if discarded == timedelta(0) else value + timedelta(minutes=minutes)


def _aware(target_date: date, value: time) -> datetime:
    return timezone.make_aware(
        datetime.combine(target_date, value), timezone.get_current_timezone()
    )


def _load_services(branch: Branch, service_ids: list[int]) -> list[BranchService]:
    unique_ids = list(dict.fromkeys(service_ids))
    services = list(
        BranchService.objects.filter(
            id__in=unique_ids, branch=branch, is_active=True, service__is_active=True
        ).select_related("service")
    )
    if len(services) != len(unique_ids):
        raise ValidationError("یک یا چند خدمت انتخاب‌شده برای این شعبه معتبر نیست.")
    by_id = {service.id: service for service in services}
    return [by_id[service_id] for service_id in unique_ids]


def _candidate_staff(branch: Branch, services: list[BranchService], staff_id: int | None):
    queryset = Staff.objects.filter(branch=branch, is_active=True)
    if staff_id is not None:
        queryset = queryset.filter(id=staff_id)
    candidates = []
    service_ids = {service.id for service in services}
    for staff in queryset:
        covered = set(
            StaffService.objects.filter(staff=staff, branch_service_id__in=service_ids).values_list(
                "branch_service_id", flat=True
            )
        )
        if covered == service_ids:
            candidates.append(staff)
    return candidates


def _staff_service_values(staff: Staff, services: list[BranchService]):
    overrides = {
        item.branch_service_id: item
        for item in StaffService.objects.filter(
            staff=staff, branch_service__in=services
        ).select_related("branch_service")
    }
    values = []
    for service in services:
        override = overrides[service.id]
        values.append(
            (
                service,
                override.duration_override_minutes or service.duration_minutes,
                override.price_override if override.price_override is not None else service.price,
            )
        )
    return values


def get_available_slots(
    *,
    branch: Branch,
    service_ids: list[int],
    target_date: date,
    staff_id: int | None = None,
    now: datetime | None = None,
) -> list[AvailableSlot]:
    now = now or timezone.now()
    expire_stale_holds(now)
    services = _load_services(branch, service_ids)
    candidates = _candidate_staff(branch, services, staff_id)
    slots: list[AvailableSlot] = []

    for staff in candidates:
        shift = StaffShift.objects.filter(
            staff=staff, day_of_week=_day_of_week(target_date), is_off=False
        ).first()
        if not shift or shift.start_time is None or shift.end_time is None:
            continue
        values = _staff_service_values(staff, services)
        duration = sum(item[1] for item in values)
        total_price = sum(item[2] for item in values)
        shift_start = _aware(target_date, shift.start_time)
        shift_end = _aware(target_date, shift.end_time)
        cursor = _ceil_to_grid(max(shift_start, now), branch.slot_interval_minutes)
        busy = list(
            Booking.objects.filter(
                staff=staff,
                start_at__lt=shift_end,
                end_at__gt=shift_start,
            )
            .filter(
                Q(status=Booking.Status.CONFIRMED)
                | Q(status=Booking.Status.PENDING_PAYMENT, hold_expires_at__gt=now)
            )
            .only("start_at", "end_at")
        )
        time_offs = list(
            StaffTimeOff.objects.filter(
                staff=staff, starts_at__lt=shift_end, ends_at__gt=shift_start
            ).only("starts_at", "ends_at")
        )
        while cursor + timedelta(minutes=duration) <= shift_end:
            slot_end = cursor + timedelta(minutes=duration)
            buffer_end = slot_end + timedelta(minutes=branch.preparation_buffer_minutes)
            conflicts_booking = any(
                cursor < booking.end_at + timedelta(minutes=branch.preparation_buffer_minutes)
                and buffer_end > booking.start_at
                for booking in busy
            )
            conflicts_time_off = any(
                cursor < time_off.ends_at and slot_end > time_off.starts_at
                for time_off in time_offs
            )
            if cursor >= now and not conflicts_booking and not conflicts_time_off:
                slots.append(
                    AvailableSlot(
                        start_at=cursor,
                        end_at=slot_end,
                        staff_id=staff.id,
                        staff_name=staff.full_name,
                        total_price=total_price,
                        duration_minutes=duration,
                    )
                )
            cursor += timedelta(minutes=branch.slot_interval_minutes)
    return sorted(slots, key=lambda slot: (slot.start_at, slot.staff_name))


@transaction.atomic
def create_booking_hold(
    *,
    customer,
    branch: Branch,
    service_ids: list[int],
    staff_id: int,
    start_at: datetime,
    notes: str = "",
) -> Booking:
    now = timezone.now()
    expire_stale_holds(now)
    if timezone.is_naive(start_at):
        start_at = timezone.make_aware(start_at, timezone.get_current_timezone())
    # Acquiring existing rows plus an early write serializes competing SQLite writers.
    list(
        Booking.objects.select_for_update().filter(
            staff_id=staff_id,
            start_at__date=start_at.date(),
            status__in=(Booking.Status.PENDING_PAYMENT, Booking.Status.CONFIRMED),
        )
    )
    available = get_available_slots(
        branch=branch,
        service_ids=service_ids,
        target_date=start_at.date(),
        staff_id=staff_id,
        now=now,
    )
    chosen = next((slot for slot in available if slot.start_at == start_at), None)
    if chosen is None:
        raise ValidationError("این زمان دیگر در دسترس نیست؛ زمان دیگری انتخاب کنید.")
    booking = Booking.objects.create(
        customer=customer,
        branch=branch,
        staff_id=staff_id,
        status=Booking.Status.PENDING_PAYMENT,
        start_at=chosen.start_at,
        end_at=chosen.end_at,
        total_price=chosen.total_price,
        deposit_amount=(chosen.total_price * branch.deposit_percent) // 100,
        notes=notes,
        hold_expires_at=now + timedelta(minutes=HOLD_MINUTES),
    )
    services = _load_services(branch, service_ids)
    staff = Staff.objects.get(pk=staff_id)
    for service, duration, price in _staff_service_values(staff, services):
        BookingItem.objects.create(
            booking=booking,
            branch_service=service,
            staff=staff,
            price=price,
            duration_minutes=duration,
        )
    return booking
