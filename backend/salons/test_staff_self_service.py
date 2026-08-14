from datetime import time

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import BranchMembership, User

from .models import (
    Branch,
    BranchService,
    City,
    Salon,
    Service,
    ServiceCategory,
    Staff,
    StaffService,
    StaffShift,
)


class StaffSelfServiceTests(APITestCase):
    def setUp(self):
        owner = User.objects.create_user(phone="09125555001", role=User.Role.SALON_OWNER)
        self.user = User.objects.create_user(phone="09125555002", role=User.Role.STAFF)
        other_user = User.objects.create_user(phone="09125555003", role=User.Role.STAFF)
        city = City.objects.create(name="شهر برنامه شخصی", slug="staff-self-city")
        salon = Salon.objects.create(owner=owner, name="سالن برنامه شخصی", slug="staff-self-salon")
        branch = Branch.objects.create(
            salon=salon, city=city, name="مرکزی", address="نشانی", phone="02111111111"
        )
        self.staff = Staff.objects.create(
            branch=branch, user=self.user, first_name="سارا", last_name="احمدی"
        )
        self.other_staff = Staff.objects.create(
            branch=branch, user=other_user, first_name="مریم", last_name="محمدی"
        )
        for user in (self.user, other_user):
            BranchMembership.objects.create(
                user=user, branch=branch, role=BranchMembership.Role.STAFF
            )
        category = ServiceCategory.objects.create(name="مو", slug="staff-self-hair")
        service = Service.objects.create(salon=salon, category=category, name="کوتاهی")
        branch_service = BranchService.objects.create(
            branch=branch, service=service, price=500_000, duration_minutes=45
        )
        self.staff_service = StaffService.objects.create(
            staff=self.staff, branch_service=branch_service
        )
        self.other_shift = StaffShift.objects.create(
            staff=self.other_staff,
            day_of_week=0,
            start_time=time(9),
            end_time=time(17),
        )
        self.client.force_authenticate(self.user)

    def test_staff_lists_only_own_profile_and_schedule(self):
        staff = self.client.get(reverse("staff-list"))
        shifts = self.client.get(reverse("staff-shift-list"))

        self.assertEqual(staff.data["count"], 1)
        self.assertEqual(staff.data["results"][0]["id"], self.staff.id)
        self.assertEqual(shifts.data["count"], 0)

    def test_staff_cannot_read_salon_settings_and_branch_response_is_minimal(self):
        salons = self.client.get(reverse("salon-list"))
        branches = self.client.get(reverse("branch-list"))
        self.assertEqual(salons.data["count"], 0)
        self.assertEqual(branches.data["count"], 1)
        self.assertEqual(
            set(branches.data["results"][0]),
            {"id", "salon", "salon_name", "name", "is_active"},
        )

    def test_staff_can_set_own_shift_and_duration_but_not_price(self):
        shift = self.client.post(
            reverse("staff-shift-list"),
            {
                "staff": self.staff.id,
                "day_of_week": 0,
                "start_time": "10:00",
                "end_time": "18:00",
                "is_off": False,
            },
        )
        duration = self.client.patch(
            reverse("staff-service-detail", args=(self.staff_service.id,)),
            {"duration_override_minutes": 60},
        )
        price = self.client.patch(
            reverse("staff-service-detail", args=(self.staff_service.id,)),
            {"price_override": 1},
        )

        self.assertEqual(shift.status_code, status.HTTP_201_CREATED)
        self.assertEqual(duration.status_code, status.HTTP_200_OK)
        self.assertEqual(price.status_code, status.HTTP_400_BAD_REQUEST)

    def test_staff_can_create_multiple_non_overlapping_windows_but_not_overlap(self):
        first = self.client.post(
            reverse("staff-shift-list"),
            {"staff": self.staff.id, "day_of_week": 1, "start_time": "09:00", "end_time": "12:00"},
        )
        second = self.client.post(
            reverse("staff-shift-list"),
            {"staff": self.staff.id, "day_of_week": 1, "start_time": "14:00", "end_time": "18:00"},
        )
        overlap = self.client.post(
            reverse("staff-shift-list"),
            {"staff": self.staff.id, "day_of_week": 1, "start_time": "11:00", "end_time": "15:00"},
        )
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_201_CREATED)
        self.assertEqual(overlap.status_code, status.HTTP_400_BAD_REQUEST)

    def test_staff_can_restore_base_duration_with_null_override(self):
        self.staff_service.duration_override_minutes = 60
        self.staff_service.save(update_fields=("duration_override_minutes",))
        response = self.client.patch(
            reverse("staff-service-detail", args=(self.staff_service.id,)),
            {"duration_override_minutes": None},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["base_duration_minutes"], 45)
        self.assertEqual(response.data["effective_duration_minutes"], 45)
