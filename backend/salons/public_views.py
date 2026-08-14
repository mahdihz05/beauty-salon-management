from django.db.models import Count, Min, Prefetch, Q
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework import mixins, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated

from accounts.models import FavoriteSalon

from .filters import PublicSalonFilter
from .models import Branch, BranchService, Salon, ServiceCategory, Staff
from .public_serializers import (
    FavoriteSalonSerializer,
    PublicBranchSerializer,
    PublicCategorySerializer,
    PublicSalonDetailSerializer,
    PublicSalonListSerializer,
)


@method_decorator(cache_page(60), name="list")
class PublicCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    serializer_class = PublicCategorySerializer
    queryset = (
        ServiceCategory.objects.filter(is_active=True)
        .annotate(
            service_count=Count("services", distinct=True),
            salon_count=Count(
                "services__branch_services__branch__salon",
                filter=Q(
                    services__branch_services__is_active=True,
                    services__branch_services__branch__is_active=True,
                    services__branch_services__branch__salon__status=Salon.Status.APPROVED,
                ),
                distinct=True,
            ),
        )
        .filter(salon_count__gt=0)
        .order_by("sort_order", "name")
    )


class PublicBranchViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    serializer_class = PublicBranchSerializer
    queryset = (
        Branch.objects.filter(is_active=True, salon__status=Salon.Status.APPROVED)
        .select_related("city", "district", "salon")
        .prefetch_related(
            Prefetch(
                "branch_services",
                queryset=BranchService.objects.filter(is_active=True).select_related(
                    "service", "service__category"
                ),
            ),
            Prefetch("staff", queryset=Staff.objects.filter(is_active=True)),
        )
    )


class PublicSalonViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    lookup_field = "slug"
    filterset_class = PublicSalonFilter
    search_fields = (
        "name",
        "description",
        "branches__address",
        "services__name",
        "branches__branch_services__service__name",
        "branches__branch_services__service__category__name",
    )
    ordering_fields = ("rating_average", "review_count", "created_at", "min_price")
    ordering = ("-is_featured", "-rating_average", "name")

    def get_serializer_class(self):
        return (
            PublicSalonDetailSerializer if self.action == "retrieve" else PublicSalonListSerializer
        )

    def get_queryset(self):
        active_services = BranchService.objects.filter(is_active=True).select_related(
            "service", "service__category"
        )
        active_staff = Staff.objects.filter(is_active=True)
        branches = (
            Branch.objects.filter(is_active=True)
            .select_related("city", "district")
            .prefetch_related(
                Prefetch("branch_services", queryset=active_services),
                Prefetch("staff", queryset=active_staff),
            )
        )
        return (
            Salon.objects.filter(status=Salon.Status.APPROVED)
            .annotate(min_price=Min("branches__branch_services__price"))
            .prefetch_related(Prefetch("branches", queryset=branches), "images", "favorited_by")
            .distinct()
        )


class FavoriteSalonViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated]
    serializer_class = FavoriteSalonSerializer

    def get_queryset(self):
        queryset = FavoriteSalon.objects.select_related("salon").prefetch_related(
            "salon__branches__branch_services", "salon__images", "salon__favorited_by"
        )
        if not self.request.user.is_authenticated:
            return queryset.none()
        return queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
