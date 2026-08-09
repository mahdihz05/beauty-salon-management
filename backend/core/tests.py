from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User

from .models import AuditLog, SupportTicket


class HealthCheckTests(APITestCase):
    def test_health_check_is_public_and_reports_sqlite(self):
        response = self.client.get(reverse("health-check"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"status": "ok", "database": "sqlite"})


class SupportTicketAPITests(APITestCase):
    def setUp(self):
        self.customer = User.objects.create_user(phone="09129999001")
        self.other = User.objects.create_user(phone="09129999002")
        self.admin = User.objects.create_user(phone="09129999003", role=User.Role.ADMIN)

    def test_customer_creates_and_only_sees_own_ticket(self):
        SupportTicket.objects.create(customer=self.other, subject="دیگر", message="پیام")
        self.client.force_authenticate(self.customer)
        created = self.client.post(
            reverse("support-ticket-list"),
            {"subject": "مشکل رزرو", "message": "رزرو من نمایش داده نمی‌شود."},
        )
        listing = self.client.get(reverse("support-ticket-list"))

        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        self.assertEqual(listing.data["count"], 1)
        self.assertTrue(AuditLog.objects.filter(action="support.ticket_created").exists())

    def test_admin_lists_and_resolves_tickets_but_customer_cannot_update(self):
        ticket = SupportTicket.objects.create(
            customer=self.customer, subject="پرداخت", message="نیاز به بررسی"
        )
        self.client.force_authenticate(self.customer)
        denied = self.client.patch(
            reverse("support-ticket-detail", args=(ticket.pk,)),
            {"status": SupportTicket.Status.RESOLVED},
        )
        self.client.force_authenticate(self.admin)
        listing = self.client.get(reverse("support-ticket-list"))
        resolved = self.client.patch(
            reverse("support-ticket-detail", args=(ticket.pk,)),
            {
                "status": SupportTicket.Status.RESOLVED,
                "response": "بررسی و رفع شد.",
                "assigned_to": self.admin.pk,
            },
        )

        self.assertEqual(denied.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(listing.data["count"], 1)
        self.assertEqual(resolved.status_code, status.HTTP_200_OK)
        self.assertEqual(resolved.data["status"], SupportTicket.Status.RESOLVED)
        self.assertTrue(AuditLog.objects.filter(action="support.ticket_updated").exists())
