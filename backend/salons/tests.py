from tempfile import TemporaryDirectory

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import BranchMembership, User
from core.models import AuditLog

from .models import Branch, BranchService, City, Salon, Service, ServiceCategory, Staff


class SalonManagementAPITests(APITestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_media = TemporaryDirectory()
        cls.media_override = override_settings(MEDIA_ROOT=cls.temp_media.name)
        cls.media_override.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls.media_override.disable()
        cls.temp_media.cleanup()

    def setUp(self):
        self.owner = User.objects.create_user(
            phone="09121111111", name="مالک سالن", role=User.Role.SALON_OWNER
        )
        self.outsider = User.objects.create_user(
            phone="09122222222", name="کاربر دیگر", role=User.Role.SALON_OWNER
        )
        self.city = City.objects.create(name="تهران", slug="tehran")
        self.category = ServiceCategory.objects.create(name="مو", slug="hair")
        self.client.force_authenticate(self.owner)

    def create_salon_and_branch(self):
        salon_response = self.client.post(
            reverse("salon-list"),
            {
                "name": "سالن رزگلد",
                "slug": "rose-gold",
                "type": Salon.Type.WOMEN,
                "description": "سالن تخصصی زیبایی",
            },
        )
        self.assertEqual(salon_response.status_code, status.HTTP_201_CREATED)
        branch_response = self.client.post(
            reverse("branch-list"),
            {
                "salon": salon_response.data["id"],
                "name": "شعبه مرکزی",
                "city": self.city.id,
                "address": "تهران، خیابان ولیعصر",
                "phone": "02188888888",
                "working_hours": {"0": ["09:00", "20:00"]},
            },
        )
        self.assertEqual(branch_response.status_code, status.HTTP_201_CREATED)
        return Salon.objects.get(pk=salon_response.data["id"]), Branch.objects.get(
            pk=branch_response.data["id"]
        )

    def test_owner_can_create_update_and_submit_salon(self):
        salon, branch = self.create_salon_and_branch()

        update_response = self.client.patch(
            reverse("branch-detail", args=(branch.id,)), {"deposit_percent": 25}
        )
        submit_response = self.client.post(reverse("salon-submit", args=(salon.id,)))

        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.assertEqual(submit_response.status_code, status.HTTP_200_OK)
        salon.refresh_from_db()
        self.assertEqual(salon.status, Salon.Status.PENDING)
        self.assertTrue(
            AuditLog.objects.filter(action="salon.submitted", target_id=str(salon.id)).exists()
        )

    def test_outsider_cannot_see_or_modify_salon(self):
        salon, _ = self.create_salon_and_branch()
        self.client.force_authenticate(self.outsider)

        list_response = self.client.get(reverse("salon-list"))
        detail_response = self.client.patch(
            reverse("salon-detail", args=(salon.id,)), {"name": "هک"}
        )

        self.assertEqual(list_response.data["count"], 0)
        self.assertEqual(detail_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_complete_service_staff_and_shift_crud(self):
        salon, branch = self.create_salon_and_branch()
        service_response = self.client.post(
            reverse("service-list"),
            {
                "salon": salon.id,
                "category": self.category.id,
                "name": "کوتاهی مو",
                "description": "کوتاهی تخصصی",
            },
        )
        self.assertEqual(service_response.status_code, status.HTTP_201_CREATED)
        branch_service_response = self.client.post(
            reverse("branch-service-list"),
            {
                "branch": branch.id,
                "service": service_response.data["id"],
                "price": 350000,
                "price_type": "fixed",
                "duration_minutes": 45,
            },
        )
        self.assertEqual(branch_service_response.status_code, status.HTTP_201_CREATED)
        staff_response = self.client.post(
            reverse("staff-list"),
            {
                "branch": branch.id,
                "first_name": "سارا",
                "last_name": "احمدی",
                "experience_years": 7,
            },
        )
        self.assertEqual(staff_response.status_code, status.HTTP_201_CREATED)
        shift_response = self.client.post(
            reverse("staff-shift-list"),
            {
                "staff": staff_response.data["id"],
                "day_of_week": 0,
                "start_time": "09:00",
                "end_time": "18:00",
            },
        )
        skill_response = self.client.post(
            reverse("staff-service-list"),
            {
                "staff": staff_response.data["id"],
                "branch_service": branch_service_response.data["id"],
            },
        )

        self.assertEqual(shift_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(skill_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(BranchService.objects.count(), 1)
        self.assertEqual(Staff.objects.get().full_name, "سارا احمدی")

    def test_branch_member_has_only_assigned_branch_access(self):
        _, branch = self.create_salon_and_branch()
        receptionist = User.objects.create_user(phone="09123333333", role=User.Role.RECEPTIONIST)
        BranchMembership.objects.create(
            user=receptionist, branch=branch, role=BranchMembership.Role.RECEPTIONIST
        )
        self.client.force_authenticate(receptionist)

        response = self.client.get(reverse("branch-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], branch.id)

    def test_receptionist_cannot_change_salon_configuration(self):
        _, branch = self.create_salon_and_branch()
        receptionist = User.objects.create_user(phone="09123333334", role=User.Role.RECEPTIONIST)
        BranchMembership.objects.create(
            user=receptionist,
            branch=branch,
            role=BranchMembership.Role.RECEPTIONIST,
        )
        self.client.force_authenticate(receptionist)
        response = self.client.patch(
            reverse("branch-detail", args=(branch.pk,)), {"phone": "02111111111"}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cross_salon_service_is_rejected(self):
        _, branch = self.create_salon_and_branch()
        other_salon = Salon.objects.create(
            owner=self.outsider, name="سالن دیگر", slug="other", type=Salon.Type.MEN
        )
        service = Service.objects.create(
            salon=other_salon, category=self.category, name="خدمت غیرمجاز"
        )

        response = self.client.post(
            reverse("branch-service-list"),
            {"branch": branch.id, "service": service.id, "price": 1, "duration_minutes": 15},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_owner_cannot_modify_central_or_other_salon_service(self):
        central = Service.objects.create(category=self.category, name="خدمت مرکزی")
        other_salon = Salon.objects.create(
            owner=self.outsider, name="سالن دیگر", slug="other-private", type=Salon.Type.MEN
        )
        private = Service.objects.create(
            salon=other_salon, category=self.category, name="خدمت خصوصی"
        )

        central_response = self.client.patch(
            reverse("service-detail", args=(central.id,)), {"name": "تغییر غیرمجاز"}
        )
        private_response = self.client.patch(
            reverse("service-detail", args=(private.id,)), {"name": "تغییر غیرمجاز"}
        )

        self.assertEqual(central_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(private_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_invalid_staff_shift_is_rejected(self):
        _, branch = self.create_salon_and_branch()
        staff = Staff.objects.create(branch=branch, first_name="علی", last_name="رضایی")

        response = self.client.post(
            reverse("staff-shift-list"),
            {
                "staff": staff.id,
                "day_of_week": 1,
                "start_time": "18:00",
                "end_time": "09:00",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_owner_can_upload_gallery_image(self):
        salon, _ = self.create_salon_and_branch()
        tiny_gif = (
            b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04"
            b"\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
        )
        image = SimpleUploadedFile("cover.gif", tiny_gif, content_type="image/gif")

        response = self.client.post(
            reverse("salon-image-list"),
            {"salon": salon.id, "image": image, "alt_text": "نمای سالن", "is_cover": True},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["is_cover"])
