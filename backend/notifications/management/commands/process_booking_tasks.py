from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from bookings.engine import expire_stale_holds
from bookings.models import Booking
from notifications.models import Notification
from notifications.services import send_booking_notification


class Command(BaseCommand):
    help = "Expire stale booking holds and send upcoming appointment reminders."

    def add_arguments(self, parser):
        parser.add_argument("--hours", type=int, default=24)
        parser.add_argument("--window-minutes", type=int, default=15)

    def handle(self, *args, **options):
        now = timezone.now()
        expired = expire_stale_holds(now)
        target = now + timedelta(hours=options["hours"])
        bookings = Booking.objects.filter(
            status=Booking.Status.CONFIRMED,
            start_at__gte=target,
            start_at__lt=target + timedelta(minutes=options["window_minutes"]),
        ).select_related("customer", "branch__salon")
        reminders = 0
        for booking in bookings:
            notification = send_booking_notification(
                booking=booking, event=Notification.Event.BOOKING_REMINDER
            )
            if notification.status == Notification.Status.SENT:
                reminders += 1
        self.stdout.write(self.style.SUCCESS(f"expired_holds={expired} reminders_sent={reminders}"))
