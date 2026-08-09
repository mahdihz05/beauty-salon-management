from django.conf import settings
from django.utils import timezone

from accounts.providers import get_sms_provider

from .models import Notification


def notification_message(booking, event: str) -> str:
    local_start = timezone.localtime(booking.start_at)
    when = f"{local_start.strftime('%Y/%m/%d')} ساعت {local_start.strftime('%H:%M')}"
    salon = booking.branch.salon.name
    messages = {
        Notification.Event.BOOKING_CONFIRMED: f"رزرو شما در {salon} برای {when} تأیید شد.",
        Notification.Event.BOOKING_REMINDER: f"یادآوری: نوبت شما در {salon} برای {when} است.",
        Notification.Event.BOOKING_CANCELLED: f"رزرو شما در {salon} برای {when} لغو شد.",
    }
    return messages[event]


def send_booking_notification(*, booking, event: str) -> Notification:
    notification, created = Notification.objects.get_or_create(
        recipient=booking.customer,
        booking=booking,
        event=event,
        channel=Notification.Channel.SMS,
        defaults={"message": notification_message(booking, event)},
    )
    if not created and notification.status == Notification.Status.SENT:
        return notification
    try:
        notification.provider_ref = get_sms_provider(settings.OTP_PROVIDER).send_message(
            booking.customer.phone, notification.message
        )
        notification.status = Notification.Status.SENT
        notification.sent_at = timezone.now()
        notification.error = ""
    except Exception as exc:  # pragma: no cover - real providers are deployment-specific
        notification.status = Notification.Status.FAILED
        notification.error = str(exc)[:500]
    notification.save(update_fields=("provider_ref", "status", "sent_at", "error"))
    return notification
