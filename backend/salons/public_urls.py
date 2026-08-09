from rest_framework.routers import DefaultRouter

from .public_views import (
    FavoriteSalonViewSet,
    PublicBranchViewSet,
    PublicCategoryViewSet,
    PublicSalonViewSet,
)

router = DefaultRouter()
router.register("salons", PublicSalonViewSet, basename="public-salon")
router.register("branches", PublicBranchViewSet, basename="public-branch")
router.register("categories", PublicCategoryViewSet, basename="public-category")
router.register("favorites", FavoriteSalonViewSet, basename="favorite-salon")

urlpatterns = router.urls
