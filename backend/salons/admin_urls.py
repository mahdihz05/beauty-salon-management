from django.urls import path
from rest_framework.routers import DefaultRouter

from .admin_views import (
    AdminCategoryViewSet,
    AdminCityViewSet,
    AdminDashboardView,
    AdminDistrictViewSet,
    AdminSalonViewSet,
)

router = DefaultRouter()
router.register("salons", AdminSalonViewSet, basename="admin-salon")
router.register("cities", AdminCityViewSet, basename="admin-city")
router.register("districts", AdminDistrictViewSet, basename="admin-district")
router.register("categories", AdminCategoryViewSet, basename="admin-category")

urlpatterns = [path("dashboard/", AdminDashboardView.as_view(), name="admin-dashboard")]
urlpatterns += router.urls
