from django.test import SimpleTestCase
from django.urls import resolve


class FrontendAdminRouteTests(SimpleTestCase):
    def test_react_admin_routes_are_served_by_spa(self):
        self.assertEqual(resolve("/admin/finance").url_name, "frontend-spa")
        self.assertEqual(resolve("/admin/support").url_name, "frontend-spa")

    def test_django_admin_remains_available_on_separate_path(self):
        self.assertEqual(resolve("/django-admin/login/").url_name, "login")
