from datetime import datetime, time, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import BranchMembership, User
from salons.models import (
    Branch,
    BranchService,
    City,
    Salon,
    Service,
    ServiceCategory,
    Staff,
    StaffService,
    StaffShift,
    StaffTimeOff,
)

from .engine import create_booking_hold, get_available_slots
from .models import Booking


class BookingEngineBase:
    def setUp(self):
        self.owner = User.objects.create_user(phone="09126666660", role=User.Role.SALON_OWNER)
        self.customer = User.objects.create_user(phone="09126666661")
        city = City.objects.create(name="تهران", slug="booking-tehran")
        salon = Salon.objects.create(
            owner=self.owner,
            name="سالن رزرو",
            slug="booking-salon",
            type=Salon.Type.WOMEN,
            status=Salon.Status.APPROVED,
        )
        self.branch = Branch.objects.create(
            salon=salon,
            city=city,
            name="مرکزی",
            address="تهران",
            phone="02122222222",
            slot_interval_minutes=15,
            preparation_buffer_minutes=10,
            deposit_percent=20,
        )
        category = ServiceCategory.objects.create(name="رزرو مو", slug="booking-hair")
        service_one = Service.objects.create(salon=salon, category=category, name="کوتاهی رزرو")
        service_two = Service.objects.create(salon=salon, category=category, name="رنگ رزرو")
        self.service_one = BranchService.objects.create(
            branch=self.branch, service=service_one, price=100000, duration_minutes=30
        )
        self.service_two = BranchService.objects.create(
            branch=self.branch, service=service_two, price=200000, duration_minutes=45
        )
        self.staff_one = Staff.objects.create(
            branch=self.branch, first_name="سارا", last_name="احمدی"
        )
        self.staff_two = Staff.objects.create(
            branch=self.branch, first_name="مریم", last_name="رضایی"
        )
        StaffService.objects.create(staff=self.staff_one, branch_service=self.service_one)
        StaffService.objects.create(staff=self.staff_one, branch_service=self.service_two)
        StaffService.objects.create(staff=self.staff_two, branch_service=self.service_one)
        self.target_date = timezone.localdate() + timedelta(days=2)
        day = (self.target_date.weekday() + 2) % 7
        for staff in (self.staff_one, self.staff_two):
            StaffShift.objects.create(
                staff=staff,
                day_of_week=day,
                start_time=time(9, 0),
                end_time=time(13, 0),
            )
        self.reference_now = timezone.make_aware(
            datetime.combine(self.target_date, time(8, 0)), timezone.get_current_timezone()
        )

    def at(self, hour, minute=0):
        return timezone.make_aware(
            datetime.combine(self.target_date, time(hour, minute)),
            timezone.get_current_timezone(),
        )


class BookingEngineTests(BookingEngineBase, TestCase):
    def test_multiple_services_use_one_qualified_staff_and_sum_duration(self):
        slots = get_available_slots(
            branch=self.branch,
            service_ids=[self.service_one.id, self.service_two.id],
            target_date=self.target_date,
            now=self.reference_now,
        )

        self.assertTrue(slots)
        self.assertEqual({slot.staff_id for slot in slots}, {self.staff_one.id})
        self.assertEqual(slots[0].duration_minutes, 75)
        self.assertEqual(slots[0].total_price, 300000)

    def test_any_available_staff_returns_every_qualified_staff(self):
        slots = get_available_slots(
            branch=self.branch,
            service_ids=[self.service_one.id],
            target_date=self.target_date,
            now=self.reference_now,
        )

        self.assertEqual({slot.staff_id for slot in slots}, {self.staff_one.id, self.staff_two.id})

    def test_existing_booking_and_buffer_remove_overlapping_slots(self):
        Booking.objects.create(
            customer=self.customer,
            branch=self.branch,
            staff=self.staff_one,
            status=Booking.Status.CONFIRMED,
            start_at=self.at(10),
            end_at=self.at(10, 30),
            total_price=100000,
        )
        slots = get_available_slots(
            branch=self.branch,
            service_ids=[self.service_one.id],
            target_date=self.target_date,
            staff_id=self.staff_one.id,
            now=self.reference_now,
        )
        starts = {slot.start_at for slot in slots}

        self.assertIn(self.at(9, 15), starts)
        self.assertNotIn(self.at(9, 30), starts)
        self.assertNotIn(self.at(10, 30), starts)
        self.assertIn(self.at(10, 45), starts)

    def test_expired_hold_is_cancelled_and_slot_released(self):
        hold = Booking.objects.create(
            customer=self.customer,
            branch=self.branch,
            staff=self.staff_one,
            status=Booking.Status.PENDING_PAYMENT,
            start_at=self.at(9),
            end_at=self.at(9, 30),
            total_price=100000,
            hold_expires_at=self.reference_now - timedelta(minutes=1),
        )
        slots = get_available_slots(
            branch=self.branch,
            service_ids=[self.service_one.id],
            target_date=self.target_date,
            staff_id=self.staff_one.id,
            now=self.reference_now,
        )

        hold.refresh_from_db()
        self.assertEqual(hold.status, Booking.Status.CANCELLED)
        self.assertIn(self.at(9), {slot.start_at for slot in slots})

    def test_time_off_removes_slots(self):
        StaffTimeOff.objects.create(
            staff=self.staff_one,
            starts_at=self.at(9),
            ends_at=self.at(11),
            reason="مرخصی",
        )
        slots = get_available_slots(
            branch=self.branch,
            service_ids=[self.service_one.id],
            target_date=self.target_date,
            staff_id=self.staff_one.id,
            now=self.reference_now,
        )

        self.assertTrue(all(slot.start_at >= self.at(11) for slot in slots))

    def test_hold_creation_snapshots_items_and_prevents_second_hold(self):
        start = self.at(9)
        booking = create_booking_hold(
            customer=self.customer,
            branch=self.branch,
            service_ids=[self.service_one.id, self.service_two.id],
            staff_id=self.staff_one.id,
            start_at=start,
        )

        self.assertEqual(booking.status, Booking.Status.PENDING_PAYMENT)
        self.assertEqual(booking.total_price, 300000)
        self.assertEqual(booking.deposit_amount, 60000)
        self.assertEqual(booking.items.count(), 2)
        with self.assertRaisesMessage(Exception, "این زمان دیگر در دسترس نیست"):
            create_booking_hold(
                customer=self.customer,
                branch=self.branch,
                service_ids=[self.service_one.id],
                staff_id=self.staff_one.id,
                start_at=start,
            )


class BookingAPITests(BookingEngineBase, APITestCase):
    def test_availability_is_public_but_hold_requires_authentication(self):
        availability = self.client.get(
            reverse("booking-availability"),
            {
                "branch": self.branch.id,
                "services": str(self.service_one.id),
                "date": self.target_date.isoformat(),
            },
        )
        anonymous_hold = self.client.post(
            reverse("booking-hold"),
            {
                "branch": self.branch.id,
                "service_ids": [self.service_one.id],
                "staff_id": self.staff_one.id,
                "start_at": self.at(9).isoformat(),
            },
        )

        self.assertEqual(availability.status_code, status.HTTP_200_OK)
        self.assertTrue(availability.data)
        self.assertEqual(anonymous_hold.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_customer_creates_hold_and_sees_own_booking(self):
        self.client.force_authenticate(self.customer)

        hold = self.client.post(
            reverse("booking-hold"),
            {
                "branch": self.branch.id,
                "service_ids": [self.service_one.id],
                "staff_id": self.staff_one.id,
                "start_at": self.at(9).isoformat(),
            },
        )
        bookings = self.client.get(reverse("booking-list"))

        self.assertEqual(hold.status_code, status.HTTP_201_CREATED)
        self.assertEqual(bookings.data["count"], 1)
        self.assertEqual(bookings.data["results"][0]["id"], hold.data["id"])

    def test_booking_list_filters_by_calendar_date(self):
        first = Booking.objects.create(
            customer=self.customer,
            branch=self.branch,
            staff=self.staff_one,
            start_at=self.at(9),
            end_at=self.at(9, 30),
            total_price=100000,
        )
        Booking.objects.create(
            customer=self.customer,
            branch=self.branch,
            staff=self.staff_one,
            start_at=self.at(10) + timedelta(days=1),
            end_at=self.at(10, 30) + timedelta(days=1),
            total_price=100000,
        )
        self.client.force_authenticate(self.customer)

        response = self.client.get(
            reverse("booking-list"),
            {
                "start_date": self.target_date.isoformat(),
                "end_date": self.target_date.isoformat(),
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], first.id)

    def test_receptionist_creates_confirmed_manual_booking_for_branch_customer(self):
        receptionist = User.objects.create_user(phone="09126666662", role=User.Role.RECEPTIONIST)
        BranchMembership.objects.create(
            user=receptionist,
            branch=self.branch,
            role=BranchMembership.Role.RECEPTIONIST,
        )
        self.client.force_authenticate(receptionist)

        response = self.client.post(
            reverse("booking-manual"),
            {
                "branch": self.branch.pk,
                "service_ids": [self.service_one.pk],
                "staff_id": self.staff_one.pk,
                "start_at": self.at(9).isoformat(),
                "customer_phone": "09127777777",
                "customer_name": "مشتری حضوری",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], Booking.Status.CONFIRMED)
        self.assertIsNone(response.data["hold_expires_at"])
        self.assertEqual(User.objects.get(phone="09127777777").name, "مشتری حضوری")

    def test_customer_cannot_create_manual_booking(self):
        self.client.force_authenticate(self.customer)
        response = self.client.post(
            reverse("booking-manual"),
            {
                "branch": self.branch.pk,
                "service_ids": [self.service_one.pk],
                "staff_id": self.staff_one.pk,
                "start_at": self.at(9).isoformat(),
                "customer_phone": "09127777778",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
