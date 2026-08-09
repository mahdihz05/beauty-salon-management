from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken

from core.models import AuditLog
from salons.models import Branch, City, Salon

from .models import BranchMembership, CustomerProfile, OTPChallenge, User
from .permissions import HasBranchAccess


@override_settings(DEBUG=True, OTP_PROVIDER="mock", OTP_CODE_TTL_SECONDS=120)
class OTPAuthenticationTests(APITestCase):
    phone = "09121234567"

    def request_code(self, phone=None):
        return self.client.post(reverse("otp-request"), {"phone": phone or self.phone})

    def test_request_and_verify_otp_creates_customer_and_tokens(self):
        request_response = self.request_code("+98 912 123 4567")

        self.assertEqual(request_response.status_code, status.HTTP_201_CREATED)
        self.assertRegex(request_response.data["debug_code"], r"^\d{6}$")

        verify_response = self.client.post(
            reverse("otp-verify"),
            {"phone": self.phone, "code": request_response.data["debug_code"]},
        )

        self.assertEqual(verify_response.status_code, status.HTTP_200_OK)
        self.assertIn("access", verify_response.data)
        self.assertIn("refresh", verify_response.data)
        user = User.objects.get(phone=self.phone)
        self.assertTrue(CustomerProfile.objects.filter(user=user).exists())
        self.assertTrue(AuditLog.objects.filter(actor=user, action="auth.otp_verified").exists())

    @override_settings(DEBUG=False, OTP_PROVIDER="mock", OTP_EXPOSE_MOCK_CODE=True)
    def test_mock_code_can_be_exposed_without_enabling_django_debug(self):
        response = self.request_code("09121234568")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertRegex(response.data["debug_code"], r"^\d{6}$")

    @override_settings(DEBUG=True, OTP_PROVIDER="mock", OTP_EXPOSE_MOCK_CODE=False)
    def test_mock_code_is_hidden_when_temporary_switch_is_disabled(self):
        response = self.request_code("09121234569")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertNotIn("debug_code", response.data)

    def test_consumed_code_cannot_be_reused(self):
        response = self.request_code()
        payload = {"phone": self.phone, "code": response.data["debug_code"]}
        self.assertEqual(
            self.client.post(reverse("otp-verify"), payload).status_code, status.HTTP_200_OK
        )
        self.assertEqual(
            self.client.post(reverse("otp-verify"), payload).status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_expired_code_is_rejected(self):
        response = self.request_code()
        OTPChallenge.objects.update(expires_at=timezone.now())

        verify_response = self.client.post(
            reverse("otp-verify"),
            {"phone": self.phone, "code": response.data["debug_code"]},
        )

        self.assertEqual(verify_response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_access_token_and_logout_flow(self):
        request_response = self.request_code()
        login_response = self.client.post(
            reverse("otp-verify"),
            {"phone": self.phone, "code": request_response.data["debug_code"]},
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")

        self.assertEqual(self.client.get(reverse("me")).status_code, status.HTTP_200_OK)
        logout_response = self.client.post(
            reverse("logout"), {"refresh": login_response.data["refresh"]}
        )

        self.assertEqual(logout_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(BlacklistedToken.objects.count(), 1)

    def test_wrong_code_increments_attempt_counter(self):
        request_response = self.request_code()
        wrong_code = "111111" if request_response.data["debug_code"] != "111111" else "222222"
        response = self.client.post(
            reverse("otp-verify"), {"phone": self.phone, "code": wrong_code}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(OTPChallenge.objects.get().attempts, 1)

    @override_settings(OTP_REQUEST_LIMIT_PER_HOUR=2)
    def test_request_rate_limit(self):
        self.assertEqual(self.request_code().status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.request_code().status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.request_code().status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_profile_requires_authentication_and_can_be_updated(self):
        self.assertEqual(self.client.get(reverse("me")).status_code, status.HTTP_401_UNAUTHORIZED)
        user = User.objects.create_user(phone=self.phone)
        CustomerProfile.objects.create(user=user)
        self.client.force_authenticate(user)

        response = self.client.patch(
            reverse("me"), {"name": "سارا احمدی", "profile": {"email": "sara@example.com"}}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertEqual(user.name, "سارا احمدی")
        self.assertEqual(user.customer_profile.email, "sara@example.com")


class BranchPermissionTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(phone="09120000001", role=User.Role.SALON_OWNER)
        self.member = User.objects.create_user(phone="09120000002", role=User.Role.RECEPTIONIST)
        self.outsider = User.objects.create_user(phone="09120000003", role=User.Role.RECEPTIONIST)
        city = City.objects.create(name="تهران", slug="tehran")
        salon = Salon.objects.create(
            owner=self.owner, name="سالن آزمون", slug="test-salon", type=Salon.Type.WOMEN
        )
        self.branch = Branch.objects.create(
            salon=salon, city=city, name="مرکزی", address="تهران", phone="02100000000"
        )
        BranchMembership.objects.create(
            user=self.member,
            branch=self.branch,
            role=BranchMembership.Role.RECEPTIONIST,
        )

    def test_only_owner_or_member_can_access_branch(self):
        permission = HasBranchAccess()

        self.assertTrue(permission._can_access(self.owner, self.branch.pk))
        self.assertTrue(permission._can_access(self.member, self.branch.pk))
        self.assertFalse(permission._can_access(self.outsider, self.branch.pk))


class PlatformUserDirectoryTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(phone="09128888001", role=User.Role.ADMIN)
        self.owner = User.objects.create_user(phone="09128888002", role=User.Role.SALON_OWNER)
        self.customer = User.objects.create_user(phone="09128888003", name="کاربر قابل جستجو")

    def test_admin_can_search_users_but_owner_cannot_access_directory(self):
        self.client.force_authenticate(self.admin)
        allowed = self.client.get(reverse("platform-user-list"), {"search": "قابل جستجو"})
        self.client.force_authenticate(self.owner)
        denied = self.client.get(reverse("platform-user-list"))

        self.assertEqual(allowed.status_code, status.HTTP_200_OK)
        self.assertEqual(allowed.data["count"], 1)
        self.assertEqual(allowed.data["results"][0]["phone"], self.customer.phone)
        self.assertEqual(denied.status_code, status.HTTP_403_FORBIDDEN)
