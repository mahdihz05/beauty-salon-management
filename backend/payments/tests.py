from datetime import timedelta

from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import BranchMembership, User
from bookings.models import Booking
from core.models import AuditLog
from salons.models import Branch, City, Salon, Staff

from .models import Payment, Settlement, Wallet, WalletTransaction
from .services import cancel_booking_with_policy, credit_salon_for_booking


@override_settings(ENABLE_LEGACY_PAYMENT_ENDPOINTS=True)
class PaymentAPITests(APITestCase):
    def setUp(self):
        self.customer = User.objects.create_user(phone="09120000101")
        self.other_customer = User.objects.create_user(phone="09120000102")
        self.owner = User.objects.create_user(phone="09120000103", role=User.Role.SALON_OWNER)
        self.admin = User.objects.create_user(phone="09120000104", role=User.Role.ADMIN)
        city = City.objects.create(name="شهر پرداخت", slug="payment-city")
        salon = Salon.objects.create(
            owner=self.owner,
            name="سالن پرداخت",
            slug="payment-salon",
            type=Salon.Type.WOMEN,
            status=Salon.Status.APPROVED,
        )
        self.branch = Branch.objects.create(
            salon=salon,
            city=city,
            name="شعبه مالی",
            address="نشانی",
            phone="02100000000",
            deposit_percent=20,
        )
        self.staff = Staff.objects.create(branch=self.branch, first_name="سارا")

    def make_booking(self, *, hours=48, customer=None):
        start = timezone.now() + timedelta(hours=hours)
        return Booking.objects.create(
            customer=customer or self.customer,
            branch=self.branch,
            staff=self.staff,
            start_at=start,
            end_at=start + timedelta(hours=1),
            total_price=500_000,
            deposit_amount=100_000,
            hold_expires_at=timezone.now() + timedelta(minutes=10),
        )

    def pay(self, booking, payment_type=Payment.Type.DEPOSIT):
        self.client.force_authenticate(self.customer)
        started = self.client.post(
            reverse("payment-start"), {"booking": booking.pk, "type": payment_type}
        )
        self.assertEqual(started.status_code, status.HTTP_201_CREATED)
        confirmed = self.client.post(reverse("payment-confirm", args=(started.data["id"],)))
        self.assertEqual(confirmed.status_code, status.HTTP_200_OK)
        booking.refresh_from_db()
        return started, confirmed

    def test_deposit_payment_confirms_booking_and_is_idempotent(self):
        booking = self.make_booking()
        self.client.force_authenticate(self.customer)
        first_start = self.client.post(
            reverse("payment-start"),
            {"booking": booking.pk, "type": Payment.Type.DEPOSIT},
        )
        second_start = self.client.post(
            reverse("payment-start"),
            {"booking": booking.pk, "type": Payment.Type.DEPOSIT},
        )
        self.assertEqual(first_start.data["id"], second_start.data["id"])
        started, _ = self.pay(booking)
        second_confirm = self.client.post(reverse("payment-confirm", args=(started.data["id"],)))

        self.assertEqual(started.data["amount"], 100_000)
        self.assertEqual(second_confirm.status_code, status.HTTP_200_OK)
        self.assertEqual(booking.status, Booking.Status.CONFIRMED)
        self.assertIsNone(booking.hold_expires_at)
        self.assertEqual(Payment.objects.filter(booking=booking).count(), 1)
        self.assertTrue(AuditLog.objects.filter(action="payment.confirmed").exists())

    def test_gateway_callback_uses_real_payment_url_and_confirms_without_session(self):
        booking = self.make_booking()
        self.client.force_authenticate(self.customer)
        started = self.client.post(
            reverse("payment-start"),
            {"booking": booking.pk, "type": Payment.Type.DEPOSIT},
        )
        payment = Payment.objects.get(pk=started.data["id"])
        self.assertNotIn("{payment_id}", payment.provider_data["callback_url"])
        self.assertIn(f"/{payment.pk}/callback/", payment.provider_data["callback_url"])

        self.client.force_authenticate(user=None)
        callback = self.client.get(reverse("payment-callback", args=(payment.pk,)))

        booking.refresh_from_db()
        self.assertEqual(callback.status_code, status.HTTP_302_FOUND)
        self.assertEqual(callback.url, f"/booking/success/{booking.pk}")
        self.assertEqual(booking.status, Booking.Status.CONFIRMED)
        self.assertTrue(AuditLog.objects.filter(action="payment.callback_confirmed").exists())

    def test_full_payment_uses_total_and_other_customer_cannot_pay(self):
        booking = self.make_booking()
        self.client.force_authenticate(self.other_customer)
        denied = self.client.post(
            reverse("payment-start"), {"booking": booking.pk, "type": Payment.Type.FULL}
        )
        self.assertEqual(denied.status_code, status.HTTP_400_BAD_REQUEST)

        self.client.force_authenticate(self.customer)
        response = self.client.post(
            reverse("payment-start"), {"booking": booking.pk, "type": Payment.Type.FULL}
        )
        self.assertEqual(response.data["amount"], 500_000)

    def test_expired_hold_cannot_start_payment(self):
        booking = self.make_booking()
        booking.hold_expires_at = timezone.now() - timedelta(seconds=1)
        booking.save(update_fields=("hold_expires_at",))
        self.client.force_authenticate(self.customer)
        response = self.client.post(
            reverse("payment-start"), {"booking": booking.pk, "type": Payment.Type.DEPOSIT}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Payment.objects.count(), 0)

    def test_early_cancellation_refunds_paid_amount_to_wallet(self):
        booking = self.make_booking(hours=48)
        self.pay(booking)
        response = self.client.post(reverse("booking-cancel", args=(booking.pk,)))

        booking.refresh_from_db()
        wallet = Wallet.objects.get(user=self.customer)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(booking.status, Booking.Status.CANCELLED)
        self.assertEqual(wallet.balance, 100_000)
        self.assertEqual(booking.payments.get().status, Payment.Status.REFUNDED)
        self.assertEqual(wallet.transactions.get().type, WalletTransaction.Type.REFUND)

    def test_late_cancellation_is_rejected(self):
        booking = self.make_booking(hours=2)
        self.pay(booking)
        response = self.client.post(reverse("booking-cancel", args=(booking.pk,)))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Wallet.objects.filter(user=self.customer).exists())
        self.assertEqual(booking.payments.get().status, Payment.Status.PAID)
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.CONFIRMED)

    def test_receptionist_cannot_cancel_but_can_check_in(self):
        receptionist = User.objects.create_user(phone="09120000106", role=User.Role.RECEPTIONIST)
        BranchMembership.objects.create(
            user=receptionist,
            branch=self.branch,
            role=BranchMembership.Role.RECEPTIONIST,
        )
        booking = self.make_booking()
        booking.status = Booking.Status.CONFIRMED
        booking.hold_expires_at = None
        booking.save(update_fields=("status", "hold_expires_at"))
        self.client.force_authenticate(receptionist)

        cancelled = self.client.post(reverse("booking-cancel", args=(booking.pk,)))
        checked_in = self.client.post(reverse("booking-check-in", args=(booking.pk,)))

        self.assertEqual(cancelled.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(checked_in.status_code, status.HTTP_200_OK)
        booking.refresh_from_db()
        self.assertEqual(booking.checked_in_by, receptionist)

    def test_receptionist_cannot_check_in_walk_in_booking(self):
        receptionist = User.objects.create_user(phone="09120000116", role=User.Role.RECEPTIONIST)
        BranchMembership.objects.create(
            user=receptionist, branch=self.branch, role=BranchMembership.Role.RECEPTIONIST
        )
        booking = self.make_booking()
        booking.status = Booking.Status.CONFIRMED
        booking.source = Booking.Source.WALK_IN
        booking.hold_expires_at = None
        booking.save(update_fields=("status", "source", "hold_expires_at"))
        self.client.force_authenticate(receptionist)
        response = self.client.post(reverse("booking-check-in", args=(booking.pk,)))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_exact_24_hour_cancellation_boundary_is_allowed(self):
        now = timezone.now()
        booking = self.make_booking()
        booking.start_at = now + timedelta(hours=24)
        booking.end_at = booking.start_at + timedelta(hours=1)
        booking.save(update_fields=("start_at", "end_at"))
        cancelled, _ = cancel_booking_with_policy(booking_id=booking.id, reason="boundary", now=now)
        self.assertEqual(cancelled.status, Booking.Status.CANCELLED)

    @override_settings(ENABLE_LEGACY_PAYMENT_ENDPOINTS=False)
    def test_legacy_gateway_start_is_disabled_for_new_flow(self):
        self.client.force_authenticate(self.customer)
        response = self.client.post(
            reverse("payment-start"), {"booking": self.make_booking().id, "type": Payment.Type.FULL}
        )
        self.assertEqual(response.status_code, status.HTTP_410_GONE)

    def test_branch_manager_finance_does_not_include_other_branch(self):
        manager = User.objects.create_user(phone="09120000117", role=User.Role.BRANCH_MANAGER)
        BranchMembership.objects.create(
            user=manager, branch=self.branch, role=BranchMembership.Role.MANAGER
        )
        other_branch = Branch.objects.create(
            salon=self.branch.salon,
            city=self.branch.city,
            name="شعبه دوم",
            address="نشانی",
            phone="02100000009",
        )
        other_staff = Staff.objects.create(branch=other_branch, first_name="مریم")
        own_booking = self.make_booking()
        other_booking = Booking.objects.create(
            customer=self.customer,
            branch=other_branch,
            staff=other_staff,
            start_at=timezone.now() + timedelta(days=3),
            end_at=timezone.now() + timedelta(days=3, hours=1),
            total_price=900_000,
        )
        Payment.objects.create(
            booking=own_booking, amount=100_000, type=Payment.Type.FULL, status=Payment.Status.PAID
        )
        Payment.objects.create(
            booking=other_booking,
            amount=900_000,
            type=Payment.Type.FULL,
            status=Payment.Status.PAID,
        )
        self.client.force_authenticate(manager)
        summary = self.client.get(reverse("salon-finance-summary"))
        detail = self.client.get(reverse("salon-finance-detail", args=(self.branch.salon_id,)))
        self.assertEqual(summary.data["results"][0]["gross_revenue"], 100_000)
        self.assertEqual(summary.data["results"][0]["branch_count"], 1)
        self.assertEqual([row["id"] for row in detail.data["branches"]], [self.branch.id])

    def test_card_to_card_receipt_requires_manager_verification(self):
        manager = User.objects.create_user(phone="09120000107", role=User.Role.BRANCH_MANAGER)
        BranchMembership.objects.create(
            user=manager, branch=self.branch, role=BranchMembership.Role.MANAGER
        )
        booking = self.make_booking()
        self.client.force_authenticate(self.customer)
        submitted = self.client.post(
            reverse("payment-submit"),
            {
                "booking": booking.pk,
                "type": Payment.Type.DEPOSIT,
                "method": Payment.Method.CARD_TO_CARD,
                "tracking_code": "987654",
            },
        )
        booking.refresh_from_db()
        self.assertEqual(submitted.status_code, status.HTTP_201_CREATED)
        self.assertEqual(booking.status, Booking.Status.AWAITING_VERIFICATION)

        self.client.force_authenticate(manager)
        verified = self.client.post(
            reverse("payment-verify-transfer", args=(submitted.data["id"],)),
            {"status": Payment.Status.PAID},
        )
        booking.refresh_from_db()
        self.assertEqual(verified.status_code, status.HTTP_200_OK)
        self.assertEqual(booking.status, Booking.Status.CONFIRMED)

    @override_settings(PLATFORM_COMMISSION_PERCENT=10)
    def test_completion_credits_owner_once_after_commission(self):
        booking = self.make_booking()
        self.pay(booking, Payment.Type.FULL)
        booking.status = Booking.Status.COMPLETED
        booking.save(update_fields=("status",))

        first = credit_salon_for_booking(booking_id=booking.pk)
        second = credit_salon_for_booking(booking_id=booking.pk)

        wallet = Wallet.objects.get(user=self.owner)
        self.assertEqual(first, 450_000)
        self.assertEqual(second, 0)
        self.assertEqual(wallet.balance, 450_000)
        self.assertEqual(wallet.transactions.count(), 2)

    @override_settings(PLATFORM_COMMISSION_PERCENT=10)
    def test_no_show_status_endpoint_credits_owner_and_audits_event(self):
        booking = self.make_booking()
        self.pay(booking)
        self.client.force_authenticate(self.owner)
        response = self.client.post(
            reverse("booking-set-status", args=(booking.pk,)),
            {"status": Booking.Status.NO_SHOW},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Wallet.objects.get(user=self.owner).balance, 90_000)
        log = AuditLog.objects.get(action="booking.status_changed")
        self.assertEqual(log.metadata["credited_amount"], 90_000)

    def test_owner_requests_settlement_and_admin_marks_it_paid(self):
        wallet = Wallet.objects.create(user=self.owner, balance=300_000)
        self.client.force_authenticate(self.owner)
        requested = self.client.post(
            reverse("settlement-list"),
            {"amount": 200_000, "bank_account": "IR000000000000000000000000"},
        )
        wallet.refresh_from_db()
        self.assertEqual(requested.status_code, status.HTTP_201_CREATED)
        self.assertEqual(wallet.balance, 100_000)

        self.client.force_authenticate(self.admin)
        processed = self.client.post(
            reverse("settlement-process", args=(requested.data["id"],)),
            {"status": Settlement.Status.PAID, "note": "واریز شد"},
        )
        self.assertEqual(processed.status_code, status.HTTP_200_OK)
        self.assertEqual(processed.data["status"], Settlement.Status.PAID)

    def test_owner_records_cash_remainder_before_completion(self):
        booking = self.make_booking()
        self.pay(booking)
        self.client.force_authenticate(self.owner)

        blocked_completion = self.client.post(
            reverse("booking-set-status", args=(booking.pk,)),
            {"status": Booking.Status.COMPLETED},
        )
        remainder = self.client.post(
            reverse("payment-remainder"),
            {"booking": booking.pk, "method": Payment.Method.CASH},
        )
        completion = self.client.post(
            reverse("booking-set-status", args=(booking.pk,)),
            {"status": Booking.Status.COMPLETED},
        )

        self.assertEqual(blocked_completion.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(remainder.status_code, status.HTTP_201_CREATED)
        self.assertEqual(remainder.data["amount"], 400_000)
        self.assertEqual(remainder.data["type"], Payment.Type.REMAINDER)
        self.assertEqual(completion.status_code, status.HTTP_200_OK)
        self.assertEqual(Wallet.objects.get(user=self.owner).balance, 450_000)
        self.assertTrue(AuditLog.objects.filter(action="payment.remainder_recorded").exists())

    def test_receptionist_records_in_person_payment_but_cannot_view_customer_directory(self):
        receptionist = User.objects.create_user(phone="09120000105", role=User.Role.RECEPTIONIST)
        BranchMembership.objects.create(
            user=receptionist,
            branch=self.branch,
            role=BranchMembership.Role.RECEPTIONIST,
        )
        booking = self.make_booking()
        self.pay(booking)
        self.client.force_authenticate(receptionist)

        remainder = self.client.post(
            reverse("payment-remainder"), {"booking": booking.pk, "method": "cash"}
        )
        customer_directory = self.client.get(reverse("customer-list"))

        self.assertEqual(remainder.status_code, status.HTTP_201_CREATED)
        self.assertEqual(customer_directory.data["count"], 0)

    def test_admin_sees_payments_and_booking_directory(self):
        booking = self.make_booking()
        self.pay(booking)
        self.client.force_authenticate(self.admin)

        payments = self.client.get(reverse("payment-list"))
        bookings = self.client.get(reverse("booking-list"))

        self.assertEqual(payments.data["count"], 1)
        self.assertEqual(bookings.data["count"], 1)

    def test_rejected_settlement_returns_reserved_balance(self):
        wallet = Wallet.objects.create(user=self.owner, balance=250_000)
        self.client.force_authenticate(self.owner)
        requested = self.client.post(
            reverse("settlement-list"),
            {"amount": 200_000, "bank_account": "IR000000000000000000000000"},
        )
        self.client.force_authenticate(self.admin)
        self.client.post(
            reverse("settlement-process", args=(requested.data["id"],)),
            {"status": Settlement.Status.REJECTED},
        )
        wallet.refresh_from_db()
        self.assertEqual(wallet.balance, 250_000)

    def test_customer_cannot_request_or_process_settlement(self):
        Wallet.objects.create(user=self.customer, balance=300_000)
        self.client.force_authenticate(self.customer)
        create_response = self.client.post(
            reverse("settlement-list"), {"amount": 10_000, "bank_account": "IR123"}
        )
        process_response = self.client.post(
            reverse("settlement-process", args=(999,)), {"status": Settlement.Status.PAID}
        )
        self.assertEqual(create_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(process_response.status_code, status.HTTP_403_FORBIDDEN)
