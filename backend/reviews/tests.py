from datetime import timedelta
from tempfile import TemporaryDirectory

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from bookings.models import Booking
from core.models import AuditLog
from salons.models import Branch, City, Salon, Staff

from .models import Review


class ReviewAPITests(APITestCase):
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
        self.customer = User.objects.create_user(phone="09121111001", name="مشتری")
        self.other = User.objects.create_user(phone="09121111002")
        self.owner = User.objects.create_user(phone="09121111003", role=User.Role.SALON_OWNER)
        self.admin = User.objects.create_user(phone="09121111004", role=User.Role.ADMIN)
        city = City.objects.create(name="شهر نظر", slug="review-city")
        self.salon = Salon.objects.create(
            owner=self.owner,
            name="سالن نظر",
            slug="review-salon",
            type=Salon.Type.WOMEN,
            status=Salon.Status.APPROVED,
        )
        branch = Branch.objects.create(
            salon=self.salon,
            city=city,
            name="مرکزی",
            address="نشانی",
            phone="02100000001",
        )
        staff = Staff.objects.create(branch=branch, first_name="مینا")
        now = timezone.now()
        self.completed = Booking.objects.create(
            customer=self.customer,
            branch=branch,
            staff=staff,
            status=Booking.Status.COMPLETED,
            start_at=now - timedelta(days=1),
            end_at=now - timedelta(days=1) + timedelta(hours=1),
            total_price=100_000,
        )
        self.confirmed = Booking.objects.create(
            customer=self.customer,
            branch=branch,
            staff=staff,
            status=Booking.Status.CONFIRMED,
            start_at=now + timedelta(days=1),
            end_at=now + timedelta(days=1, hours=1),
            total_price=100_000,
        )
        self.payload = {
            "booking": self.completed.pk,
            "overall_rating": 5,
            "quality_rating": 5,
            "cleanliness_rating": 4,
            "behavior_rating": 5,
            "value_rating": 4,
            "comment": "خدمات بسیار خوب بود.",
        }

    def test_customer_can_review_completed_booking_once(self):
        self.client.force_authenticate(self.customer)
        created = self.client.post(reverse("my-review-list"), self.payload)
        duplicate = self.client.post(reverse("my-review-list"), self.payload)

        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        self.assertEqual(created.data["status"], Review.Status.PENDING)
        self.assertEqual(created.data["value_rating"], 4)
        self.assertEqual(created.data["staff"], self.completed.staff_id)
        self.assertEqual(duplicate.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(AuditLog.objects.filter(action="review.created").exists())

    def test_review_accepts_customer_image(self):
        image = SimpleUploadedFile(
            "result.gif",
            b"GIF87a\x01\x00\x01\x00\x80\x01\x00\x00\x00\x00ccc,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;",
            content_type="image/gif",
        )
        self.client.force_authenticate(self.customer)
        response = self.client.post(
            reverse("my-review-list"),
            {**self.payload, "uploaded_images": [image]},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Review.objects.get().images.count(), 1)

    def test_non_completed_or_other_users_booking_cannot_be_reviewed(self):
        self.client.force_authenticate(self.customer)
        payload = {**self.payload, "booking": self.confirmed.pk}
        confirmed_response = self.client.post(reverse("my-review-list"), payload)
        self.client.force_authenticate(self.other)
        other_response = self.client.post(reverse("my-review-list"), self.payload)

        self.assertEqual(confirmed_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(other_response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_pending_review_is_not_public(self):
        Review.objects.create(
            booking=self.completed,
            customer=self.customer,
            salon=self.salon,
            status=Review.Status.PENDING,
            overall_rating=5,
            quality_rating=5,
            cleanliness_rating=5,
            behavior_rating=5,
            comment="در انتظار",
        )
        response = self.client.get(reverse("public-review-list"), {"salon": self.salon.pk})
        self.assertEqual(response.data["count"], 0)

    def test_admin_publication_updates_salon_average_and_count(self):
        review = Review.objects.create(
            booking=self.completed,
            customer=self.customer,
            salon=self.salon,
            overall_rating=4,
            quality_rating=4,
            cleanliness_rating=4,
            behavior_rating=4,
            comment="خوب",
        )
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            reverse("review-moderation-moderate", args=(review.pk,)),
            {"status": Review.Status.PUBLISHED},
        )

        self.salon.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(float(self.salon.rating_average), 4.0)
        self.assertEqual(self.salon.review_count, 1)
        self.assertTrue(AuditLog.objects.filter(action="review.moderated").exists())

    def test_hiding_review_removes_it_from_rating(self):
        review = Review.objects.create(
            booking=self.completed,
            customer=self.customer,
            salon=self.salon,
            status=Review.Status.PUBLISHED,
            overall_rating=2,
            quality_rating=2,
            cleanliness_rating=2,
            behavior_rating=2,
            comment="متوسط",
        )
        self.client.force_authenticate(self.admin)
        self.client.post(
            reverse("review-moderation-moderate", args=(review.pk,)),
            {"status": Review.Status.HIDDEN},
        )
        self.salon.refresh_from_db()
        self.assertEqual(self.salon.review_count, 0)
        self.assertEqual(float(self.salon.rating_average), 0)

    def test_non_admin_cannot_moderate(self):
        self.client.force_authenticate(self.owner)
        response = self.client.get(reverse("review-moderation-list"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
