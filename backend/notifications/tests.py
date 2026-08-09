from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from bookings.models import Booking
from salons.models import Branch, City, Salon, Staff

from .models import Notification
from .services import send_booking_notification


class NotificationTests(TestCase):
    def setUp(self):
        owner = User.objects.create_user(phone="09124444001", role=User.Role.SALON_OWNER)
        self.customer = User.objects.create_user(phone="09124444002")
        city = City.objects.create(name="شهر اعلان", slug="notification-city")
        salon = Salon.objects.create(
            owner=owner,
            name="سالن اعلان",
            slug="notification-salon",
            type=Salon.Type.WOMEN,
            status=Salon.Status.APPROVED,
        )
        branch = Branch.objects.create(
            salon=salon,
            city=city,
            name="مرکزی",
            address="نشانی",
            phone="02100000003",
        )
        staff = Staff.objects.create(branch=branch, first_name="ندا")
        start = timezone.now() + timedelta(hours=24, minutes=5)
        self.booking = Booking.objects.create(
            customer=self.customer,
            branch=branch,
            staff=staff,
            status=Booking.Status.CONFIRMED,
            start_at=start,
            end_at=start + timedelta(hours=1),
            total_price=100_000,
        )

    def test_mock_notification_is_sent_once_per_event(self):
        first = send_booking_notification(
            booking=self.booking, event=Notification.Event.BOOKING_CONFIRMED
        )
        second = send_booking_notification(
            booking=self.booking, event=Notification.Event.BOOKING_CONFIRMED
        )
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(first.status, Notification.Status.SENT)
        self.assertEqual(Notification.objects.count(), 1)

    def test_management_command_sends_reminder_and_is_idempotent(self):
        output = StringIO()
        call_command("process_booking_tasks", stdout=output)
        call_command("process_booking_tasks", stdout=output)
        reminders = Notification.objects.filter(event=Notification.Event.BOOKING_REMINDER)
        self.assertEqual(reminders.count(), 1)
        self.assertIn("reminders_sent=1", output.getvalue())
