from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    AvailabilityView,
    BookingViewSet,
    CreateHoldView,
    CreateManualBookingView,
    CustomerViewSet,
    DiscountCodeViewSet,
)

router = DefaultRouter()
router.register("items", BookingViewSet, basename="booking")
router.register("discounts", DiscountCodeViewSet, basename="discount")
router.register("customers", CustomerViewSet, basename="customer")

urlpatterns = [
    path("availability/", AvailabilityView.as_view(), name="booking-availability"),
    path("holds/", CreateHoldView.as_view(), name="booking-hold"),
    path("manual/", CreateManualBookingView.as_view(), name="booking-manual"),
]
urlpatterns += router.urls
