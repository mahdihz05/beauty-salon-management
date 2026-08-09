from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import FavoriteSalon, User

from .models import Branch, BranchService, City, Salon, Service, ServiceCategory, Staff


class PublicSalonAPITests(APITestCase):
    def setUp(self):
        owner = User.objects.create_user(phone="09124444444", role=User.Role.SALON_OWNER)
        self.customer = User.objects.create_user(phone="09125555555")
        self.tehran = City.objects.create(name="تهران", slug="tehran-public")
        self.shiraz = City.objects.create(name="شیراز", slug="shiraz-public")
        category = ServiceCategory.objects.create(name="پیرایش مو", slug="public-hair")
        self.category = category
        self.approved = Salon.objects.create(
            owner=owner,
            name="سالن رویال",
            slug="royal-public",
            type=Salon.Type.WOMEN,
            status=Salon.Status.APPROVED,
            rating_average="4.80",
            review_count=120,
            is_featured=True,
        )
        branch = Branch.objects.create(
            salon=self.approved,
            city=self.tehran,
            name="مرکزی",
            address="تهران، زعفرانیه",
            phone="02111111111",
        )
        service = Service.objects.create(
            salon=self.approved, category=category, name="کوتاهی و استایل"
        )
        BranchService.objects.create(
            branch=branch, service=service, price=450000, duration_minutes=45
        )
        Staff.objects.create(branch=branch, first_name="سارا", last_name="مریم", experience_years=8)
        self.pending = Salon.objects.create(
            owner=owner,
            name="سالن منتشرنشده",
            slug="not-public",
            type=Salon.Type.MEN,
            status=Salon.Status.PENDING,
        )

    def test_anonymous_user_sees_only_approved_salons(self):
        response = self.client.get(reverse("public-salon-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["slug"], self.approved.slug)

    def test_public_search_and_filters(self):
        matching = self.client.get(
            reverse("public-salon-list"),
            {"search": "رویال", "city": self.tehran.id, "type": Salon.Type.WOMEN},
        )
        wrong_city = self.client.get(reverse("public-salon-list"), {"city": self.shiraz.id})
        high_minimum = self.client.get(reverse("public-salon-list"), {"min_price": 500000})
        service_search = self.client.get(reverse("public-salon-list"), {"search": "پیرایش مو"})
        category_filter = self.client.get(
            reverse("public-salon-list"), {"category": self.category.id}
        )

        self.assertEqual(matching.data["count"], 1)
        self.assertEqual(wrong_city.data["count"], 0)
        self.assertEqual(high_minimum.data["count"], 0)
        self.assertEqual(service_search.data["count"], 1)
        self.assertEqual(category_filter.data["count"], 1)

    def test_public_categories_include_salon_and_service_counts(self):
        response = self.client.get(reverse("public-category-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["service_count"], 1)
        self.assertEqual(response.data["results"][0]["salon_count"], 1)

    def test_public_detail_contains_services_and_staff(self):
        response = self.client.get(reverse("public-salon-detail", args=(self.approved.slug,)))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["branches"][0]["services"][0]["price"], 450000)
        self.assertEqual(response.data["branches"][0]["staff"][0]["full_name"], "سارا مریم")

    def test_customer_favorites_are_private_and_unique(self):
        self.assertEqual(
            self.client.get(reverse("favorite-salon-list")).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.client.force_authenticate(self.customer)

        created = self.client.post(reverse("favorite-salon-list"), {"salon": self.approved.id})
        duplicate = self.client.post(reverse("favorite-salon-list"), {"salon": self.approved.id})
        listed = self.client.get(reverse("favorite-salon-list"))

        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        self.assertEqual(duplicate.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(listed.data["count"], 1)
        self.assertEqual(FavoriteSalon.objects.filter(user=self.customer).count(), 1)
