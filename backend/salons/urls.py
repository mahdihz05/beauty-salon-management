from rest_framework.routers import DefaultRouter

from .views import (
    BranchServiceViewSet,
    BranchViewSet,
    CityViewSet,
    DistrictViewSet,
    SalonImageViewSet,
    SalonViewSet,
    ServiceCategoryViewSet,
    ServiceViewSet,
    StaffServiceViewSet,
    StaffShiftViewSet,
    StaffTimeOffViewSet,
    StaffViewSet,
)

router = DefaultRouter()
router.register("cities", CityViewSet, basename="city")
router.register("districts", DistrictViewSet, basename="district")
router.register("salons", SalonViewSet, basename="salon")
router.register("branches", BranchViewSet, basename="branch")
router.register("categories", ServiceCategoryViewSet, basename="service-category")
router.register("services", ServiceViewSet, basename="service")
router.register("branch-services", BranchServiceViewSet, basename="branch-service")
router.register("staff", StaffViewSet, basename="staff")
router.register("staff-shifts", StaffShiftViewSet, basename="staff-shift")
router.register("staff-services", StaffServiceViewSet, basename="staff-service")
router.register("staff-time-offs", StaffTimeOffViewSet, basename="staff-time-off")
router.register("salon-images", SalonImageViewSet, basename="salon-image")

urlpatterns = router.urls
