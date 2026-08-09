from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from bookings.tests import BookingEngineBase
from notifications.models import Notification


@override_settings(DEBUG=True)
class FullBookingJourneyTests(BookingEngineBase, APITestCase):
    def test_otp_to_confirmed_booking_journey(self):
        otp_request = self.client.post(reverse("otp-request"), {"phone": self.customer.phone})
        self.assertEqual(otp_request.status_code, status.HTTP_201_CREATED)
        otp_verify = self.client.post(
            reverse("otp-verify"),
            {"phone": self.customer.phone, "code": otp_request.data["debug_code"]},
        )
        self.assertEqual(otp_verify.status_code, status.HTTP_200_OK)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {otp_verify.data['access']}")

        availability = self.client.get(
            reverse("booking-availability"),
            {
                "branch": self.branch.pk,
                "services": str(self.service_one.pk),
                "date": self.target_date.isoformat(),
            },
        )
        self.assertEqual(availability.status_code, status.HTTP_200_OK)
        slot = availability.data[0]
        hold = self.client.post(
            reverse("booking-hold"),
            {
                "branch": self.branch.pk,
                "service_ids": [self.service_one.pk],
                "staff_id": slot["staff_id"],
                "start_at": slot["start_at"],
            },
        )
        self.assertEqual(hold.status_code, status.HTTP_201_CREATED)
        payment = self.client.post(
            reverse("payment-start"), {"booking": hold.data["id"], "type": "deposit"}
        )
        self.assertEqual(payment.status_code, status.HTTP_201_CREATED)
        confirmation = self.client.post(reverse("payment-confirm", args=(payment.data["id"],)))
        self.assertEqual(confirmation.status_code, status.HTTP_200_OK)

        booking = self.client.get(reverse("booking-detail", args=(hold.data["id"],)))
        self.assertEqual(booking.data["status"], "confirmed")
        self.assertTrue(
            Notification.objects.filter(
                booking_id=hold.data["id"], event=Notification.Event.BOOKING_CONFIRMED
            ).exists()
        )
