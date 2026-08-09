from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from core.models import AuditLog

from .models import Branch, City, Salon, ServiceCategory


class PlatformAdminAPITests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            phone="09120000010", role=User.Role.ADMIN, is_staff=True
        )
        self.owner = User.objects.create_user(phone="09120000011", role=User.Role.SALON_OWNER)
        self.city = City.objects.create(name="تهران", slug="tehran")
        self.salon = Salon.objects.create(
            owner=self.owner,
            name="سالن در انتظار",
            slug="pending-salon",
            type=Salon.Type.WOMEN,
            status=Salon.Status.PENDING,
        )
        Branch.objects.create(
            salon=self.salon,
            city=self.city,
            name="مرکزی",
            address="تهران",
            phone="02100000000",
        )

    def test_non_admin_cannot_access_platform_admin_api(self):
        self.client.force_authenticate(self.owner)

        response = self.client.get(reverse("admin-dashboard"))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_dashboard_and_approval(self):
        self.client.force_authenticate(self.admin)

        dashboard = self.client.get(reverse("admin-dashboard"))
        approval = self.client.post(reverse("admin-salon-approve", args=(self.salon.id,)))

        self.assertEqual(dashboard.status_code, status.HTTP_200_OK)
        self.assertEqual(dashboard.data["pending_salons"], 1)
        self.assertEqual(approval.status_code, status.HTTP_200_OK)
        self.salon.refresh_from_db()
        self.assertEqual(self.salon.status, Salon.Status.APPROVED)
        self.assertTrue(AuditLog.objects.filter(action="salon.approved").exists())

    def test_admin_rejection_requires_reason_and_is_audited(self):
        self.client.force_authenticate(self.admin)

        invalid = self.client.post(reverse("admin-salon-reject", args=(self.salon.id,)), {})
        valid = self.client.post(
            reverse("admin-salon-reject", args=(self.salon.id,)),
            {"reason": "مدارک هویتی ناقص است."},
        )

        self.assertEqual(invalid.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(valid.status_code, status.HTTP_200_OK)
        self.salon.refresh_from_db()
        self.assertEqual(self.salon.status, Salon.Status.REJECTED)
        self.assertEqual(self.salon.rejection_reason, "مدارک هویتی ناقص است.")

    def test_admin_can_manage_city_district_and_category(self):
        self.client.force_authenticate(self.admin)

        city_response = self.client.post(
            reverse("admin-city-list"), {"name": "شیراز", "slug": "shiraz"}
        )
        district_response = self.client.post(
            reverse("admin-district-list"),
            {"city": city_response.data["id"], "name": "معالی‌آباد", "slug": "maali-abad"},
        )
        category_response = self.client.post(
            reverse("admin-category-list"), {"name": "مراقبت پوست", "slug": "skin-care"}
        )

        self.assertEqual(city_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(district_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(category_response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(ServiceCategory.objects.filter(slug="skin-care").exists())

    def test_admin_can_view_complete_salon_overview(self):
        self.client.force_authenticate(self.admin)

        response = self.client.get(reverse("admin-salon-overview", args=(self.salon.id,)))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["salon"]["id"], self.salon.id)
        self.assertEqual(response.data["salon"]["owner_phone"], self.owner.phone)
        self.assertEqual(response.data["metrics"]["branch_count"], 1)
        self.assertIn("customers", response.data)
        self.assertIn("bookings", response.data)
        self.assertIn("payments", response.data)
        self.assertIn("reviews", response.data)

    def test_non_admin_cannot_view_salon_overview(self):
        self.client.force_authenticate(self.owner)

        response = self.client.get(reverse("admin-salon-overview", args=(self.salon.id,)))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
