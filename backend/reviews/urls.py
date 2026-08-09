from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import MyReviewViewSet, PublicReviewViewSet, ReviewModerationViewSet

router = DefaultRouter()
router.register("mine", MyReviewViewSet, basename="my-review")
router.register("public", PublicReviewViewSet, basename="public-review")
router.register("moderation", ReviewModerationViewSet, basename="review-moderation")

urlpatterns = [path("", include(router.urls))]
