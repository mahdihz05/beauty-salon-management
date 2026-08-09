from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import BranchMembership, User
from bookings.models import Booking, BookingItem
from payments.models import Payment
from salons.models import Branch, BranchService, City, Salon, Service, ServiceCategory, Staff


class ReportingTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(phone="09125555001", role=User.Role.SALON_OWNER)
        self.other_owner = User.objects.create_user(phone="09125555002", role=User.Role.SALON_OWNER)
        customer = User.objects.create_user(phone="09125555003")
        city = City.objects.create(name="شهر گزارش", slug="report-city")
        salon = Salon.objects.create(
            owner=self.owner,
            name="سالن گزارش",
            slug="report-salon",
            type=Salon.Type.WOMEN,
            status=Salon.Status.APPROVED,
        )
        self.branch = Branch.objects.create(
            salon=salon,
            city=city,
            name="مرکزی",
            address="نشانی",
            phone="02100000004",
        )
        category = ServiceCategory.objects.create(name="گزارش", slug="report-service")
        service = Service.objects.create(salon=salon, category=category, name="اصلاح")
        branch_service = BranchService.objects.create(
            branch=self.branch, service=service, price=200_000, duration_minutes=30
        )
        staff = Staff.objects.create(branch=self.branch, first_name="مهسا")
        start = timezone.now() - timedelta(hours=2)
        booking = Booking.objects.create(
            customer=customer,
            branch=self.branch,
            staff=staff,
            status=Booking.Status.COMPLETED,
            start_at=start,
            end_at=start + timedelta(minutes=30),
            total_price=200_000,
        )
        BookingItem.objects.create(
            booking=booking,
            branch_service=branch_service,
            staff=staff,
            price=200_000,
            duration_minutes=30,
        )
        Payment.objects.create(
            booking=booking,
            amount=200_000,
            type=Payment.Type.FULL,
            status=Payment.Status.PAID,
            paid_at=timezone.now(),
        )

    def test_owner_sees_scoped_summary_and_top_service(self):
        self.client.force_authenticate(self.owner)
        response = self.client.get(reverse("report-summary"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["gross_revenue"], 200_000)
        self.assertEqual(response.data["net_revenue"], 180_000)
        self.assertEqual(response.data["top_services"][0]["service_name"], "اصلاح")

    def test_other_owner_cannot_request_branch_report(self):
        self.client.force_authenticate(self.other_owner)
        response = self.client.get(reverse("report-summary"), {"branch": self.branch.pk})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_receptionist_has_no_financial_report_access(self):
        receptionist = User.objects.create_user(phone="09125555004", role=User.Role.RECEPTIONIST)
        BranchMembership.objects.create(
            user=receptionist,
            branch=self.branch,
            role=BranchMembership.Role.RECEPTIONIST,
        )
        self.client.force_authenticate(receptionist)
        response = self.client.get(reverse("report-summary"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_csv_has_utf8_bom_and_financial_row(self):
        self.client.force_authenticate(self.owner)
        response = self.client.get(reverse("report-financial-csv"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.content.startswith(b"\xef\xbb\xbf"))
        self.assertIn(b"200000", response.content)
