from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from payments.models import Payment
from salons.models import (
    Branch,
    BranchService,
    City,
    Salon,
    Service,
    ServiceCategory,
    Staff,
)

from .models import Booking, BookingItem, DiscountCode, DiscountRedemption


class DiscountAndCustomerTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(phone="09123333001", role=User.Role.SALON_OWNER)
        self.customer = User.objects.create_user(phone="09123333002", name="مشتری وفادار")
        self.other_owner = User.objects.create_user(phone="09123333003", role=User.Role.SALON_OWNER)
        city = City.objects.create(name="شهر تخفیف", slug="discount-city")
        self.salon = Salon.objects.create(
            owner=self.owner,
            name="سالن تخفیف",
            slug="discount-salon",
            type=Salon.Type.WOMEN,
            status=Salon.Status.APPROVED,
        )
        self.branch = Branch.objects.create(
            salon=self.salon,
            city=city,
            name="شعبه تخفیف",
            address="نشانی",
            phone="02100000002",
            deposit_percent=20,
        )
        category = ServiceCategory.objects.create(name="تخفیف", slug="discount-service")
        service = Service.objects.create(salon=self.salon, category=category, name="خدمت")
        self.branch_service = BranchService.objects.create(
            branch=self.branch, service=service, price=500_000, duration_minutes=60
        )
        self.staff = Staff.objects.create(branch=self.branch, first_name="مونا")
        start = timezone.now() + timedelta(days=2)
        self.booking = Booking.objects.create(
            customer=self.customer,
            branch=self.branch,
            staff=self.staff,
            start_at=start,
            end_at=start + timedelta(hours=1),
            total_price=500_000,
            deposit_amount=100_000,
            hold_expires_at=timezone.now() + timedelta(minutes=10),
        )
        BookingItem.objects.create(
            booking=self.booking,
            branch_service=self.branch_service,
            staff=self.staff,
            price=500_000,
            duration_minutes=60,
        )
        self.discount = DiscountCode.objects.create(
            code="WELCOME20",
            salon=self.salon,
            type=DiscountCode.Type.PERCENT,
            value=20,
            maximum_discount=80_000,
            usage_limit=1,
            starts_at=timezone.now() - timedelta(hours=1),
            ends_at=timezone.now() + timedelta(days=3),
        )

    def test_discount_changes_payment_and_is_redeemed_on_confirmation(self):
        self.client.force_authenticate(self.customer)
        started = self.client.post(
            reverse("payment-start"),
            {"booking": self.booking.pk, "type": "full", "discount_code": "welcome20"},
        )
        confirmed = self.client.post(reverse("payment-confirm", args=(started.data["id"],)))

        self.booking.refresh_from_db()
        self.discount.refresh_from_db()
        self.assertEqual(started.status_code, status.HTTP_201_CREATED)
        self.assertEqual(started.data["amount"], 420_000)
        self.assertEqual(confirmed.status_code, status.HTTP_200_OK)
        self.assertEqual(self.booking.discount_amount, 80_000)
        self.assertEqual(self.discount.used_count, 1)
        self.assertTrue(DiscountRedemption.objects.filter(booking=self.booking).exists())

    def test_invalid_or_expired_code_is_rejected(self):
        self.discount.ends_at = timezone.now() - timedelta(seconds=1)
        self.discount.save(update_fields=("ends_at",))
        self.client.force_authenticate(self.customer)
        response = self.client.post(
            reverse("payment-start"),
            {"booking": self.booking.pk, "type": "full", "discount_code": "WELCOME20"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Payment.objects.count(), 0)

    def test_owner_can_manage_own_codes_but_not_another_salon(self):
        self.client.force_authenticate(self.other_owner)
        listing = self.client.get(reverse("discount-list"))
        update = self.client.patch(
            reverse("discount-detail", args=(self.discount.pk,)), {"is_active": False}
        )
        self.assertEqual(listing.data["count"], 0)
        self.assertEqual(update.status_code, status.HTTP_404_NOT_FOUND)

    def test_customer_directory_is_scoped_to_salon_owner(self):
        Payment.objects.create(
            booking=self.booking,
            amount=100_000,
            type=Payment.Type.DEPOSIT,
            status=Payment.Status.PAID,
        )
        self.client.force_authenticate(self.owner)
        owner_response = self.client.get(reverse("customer-list"))
        self.client.force_authenticate(self.other_owner)
        other_response = self.client.get(reverse("customer-list"))

        self.assertEqual(owner_response.data["count"], 1)
        self.assertEqual(owner_response.data["results"][0]["phone"], self.customer.phone)
        self.assertEqual(owner_response.data["results"][0]["total_spent"], 100_000)
        self.assertEqual(other_response.data["count"], 0)
