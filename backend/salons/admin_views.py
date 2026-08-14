from django.db.models import Count, Max, Prefetch, Q, Sum
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.generics import GenericAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from accounts.models import User
from accounts.permissions import IsPlatformAdmin
from core.audit import record_audit

from .admin_serializers import (
    AdminCategorySerializer,
    AdminCitySerializer,
    AdminDashboardSerializer,
    AdminDistrictSerializer,
    RejectionSerializer,
)
from .models import Branch, BranchService, City, District, Salon, Service, ServiceCategory, Staff
from .serializers import BranchSerializer, BranchServiceSerializer, SalonSerializer, StaffSerializer


class AdminSalonPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = "page_size"
    max_page_size = 250


class AdminDashboardView(GenericAPIView):
    permission_classes = [IsPlatformAdmin]
    serializer_class = AdminDashboardSerializer

    @extend_schema(responses=AdminDashboardSerializer)
    def get(self, request):
        data = {
            "users": User.objects.count(),
            "salons": Salon.objects.count(),
            "pending_salons": Salon.objects.filter(status=Salon.Status.PENDING).count(),
            "approved_salons": Salon.objects.filter(status=Salon.Status.APPROVED).count(),
            "branches": Branch.objects.count(),
            "services": Service.objects.count(),
        }
        return Response(self.get_serializer(data).data)


class AdminSalonViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsPlatformAdmin]
    serializer_class = SalonSerializer
    pagination_class = AdminSalonPagination
    queryset = Salon.objects.select_related("owner").prefetch_related(
        Prefetch("branches", queryset=Branch.objects.select_related("city", "district")),
        "images",
    )
    filterset_fields = ("status", "type")
    search_fields = ("name", "owner__name", "owner__phone")
    ordering_fields = ("created_at", "updated_at", "name")

    @action(detail=True, methods=("get",), url_path="overview")
    def overview(self, request, pk=None):
        """Complete read-only operational view of one salon for platform admins."""
        from bookings.models import Booking, DiscountCode
        from bookings.serializers import BookingSerializer, DiscountCodeSerializer
        from payments.models import Payment
        from payments.serializers import PaymentSerializer
        from reviews.models import Review
        from reviews.serializers import ReviewSerializer

        salon = self.get_object()
        branches = Branch.objects.filter(salon=salon).select_related("city", "district")
        branch_ids = list(branches.values_list("id", flat=True))
        branch_services = BranchService.objects.filter(branch_id__in=branch_ids).select_related(
            "branch", "service", "service__category"
        )
        staff = (
            Staff.objects.filter(branch_id__in=branch_ids)
            .select_related("branch", "user")
            .prefetch_related("shifts", "staff_services__branch_service__service")
        )
        bookings = (
            Booking.objects.filter(branch_id__in=branch_ids)
            .select_related("customer", "branch", "branch__salon", "staff", "discount_code")
            .prefetch_related("items", "items__branch_service__service", "items__staff", "payments")
        )
        payments = Payment.objects.filter(booking__branch_id__in=branch_ids).select_related(
            "booking", "booking__customer", "booking__branch", "booking__branch__salon"
        )
        reviews = (
            Review.objects.filter(salon=salon)
            .select_related("customer", "salon", "staff", "booking")
            .prefetch_related("images")
        )
        discounts = DiscountCode.objects.filter(salon=salon)

        booking_stats = bookings.aggregate(
            booking_count=Count("id"),
            completed_count=Count("id", filter=Q(status=Booking.Status.COMPLETED)),
            confirmed_count=Count("id", filter=Q(status=Booking.Status.CONFIRMED)),
            cancelled_count=Count("id", filter=Q(status=Booking.Status.CANCELLED)),
            no_show_count=Count("id", filter=Q(status=Booking.Status.NO_SHOW)),
            gross_revenue=Sum("total_price", filter=Q(status=Booking.Status.COMPLETED)),
        )
        paid_revenue = (
            payments.filter(status=Payment.Status.PAID).aggregate(total=Sum("amount"))["total"] or 0
        )
        refunded_amount = (
            payments.filter(status=Payment.Status.REFUNDED).aggregate(total=Sum("amount"))["total"]
            or 0
        )
        customers = list(
            bookings.values("customer_id", "customer__name", "customer__phone")
            .annotate(
                booking_count=Count("id"),
                completed_count=Count("id", filter=Q(status=Booking.Status.COMPLETED)),
                total_spent=Sum("total_price", filter=Q(status=Booking.Status.COMPLETED)),
                last_booking_at=Max("start_at"),
            )
            .order_by("-last_booking_at")
        )
        for customer in customers:
            customer["id"] = customer.pop("customer_id")
            customer["name"] = customer.pop("customer__name")
            customer["phone"] = customer.pop("customer__phone")
            customer["total_spent"] = customer["total_spent"] or 0

        salon_data = SalonSerializer(salon, context={"request": request}).data
        salon_data.update(
            {
                "owner_phone": salon.owner.phone,
                "rating_average": salon.rating_average,
                "review_count": salon.review_count,
                "is_featured": salon.is_featured,
            }
        )
        return Response(
            {
                "salon": salon_data,
                "metrics": {
                    **booking_stats,
                    "gross_revenue": booking_stats["gross_revenue"] or 0,
                    "paid_revenue": paid_revenue,
                    "refunded_amount": refunded_amount,
                    "customer_count": len(customers),
                    "branch_count": len(branch_ids),
                    "service_count": branch_services.count(),
                    "staff_count": staff.count(),
                    "payment_count": payments.count(),
                    "review_count": reviews.count(),
                },
                "branches": BranchSerializer(
                    branches, many=True, context={"request": request}
                ).data,
                "services": BranchServiceSerializer(
                    branch_services, many=True, context={"request": request}
                ).data,
                "staff": StaffSerializer(staff, many=True, context={"request": request}).data,
                "customers": customers,
                "bookings": BookingSerializer(
                    bookings.order_by("-start_at")[:20], many=True, context={"request": request}
                ).data,
                "bookings_total": booking_stats["booking_count"],
                "payments": PaymentSerializer(
                    payments.order_by("-created_at")[:20], many=True, context={"request": request}
                ).data,
                "payments_total": payments.count(),
                "reviews": ReviewSerializer(reviews, many=True, context={"request": request}).data,
                "discounts": DiscountCodeSerializer(
                    discounts, many=True, context={"request": request}
                ).data,
            }
        )

    def change_status(self, request, salon, next_status, action_name, reason=""):
        previous_status = salon.status
        salon.status = next_status
        salon.rejection_reason = reason
        salon.save(update_fields=("status", "rejection_reason", "updated_at"))
        record_audit(
            request=request,
            actor=request.user,
            action=action_name,
            target=salon,
            metadata={"from": previous_status, "to": next_status, "reason": reason},
        )
        return Response(self.get_serializer(salon).data)

    @action(detail=True, methods=("post",))
    def approve(self, request, pk=None):
        return self.change_status(
            request, self.get_object(), Salon.Status.APPROVED, "salon.approved"
        )

    @action(detail=True, methods=("post",))
    def reject(self, request, pk=None):
        serializer = RejectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return self.change_status(
            request,
            self.get_object(),
            Salon.Status.REJECTED,
            "salon.rejected",
            serializer.validated_data["reason"],
        )

    @action(detail=True, methods=("post",))
    def suspend(self, request, pk=None):
        serializer = RejectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return self.change_status(
            request,
            self.get_object(),
            Salon.Status.SUSPENDED,
            "salon.suspended",
            serializer.validated_data["reason"],
        )


class AuditedAdminModelViewSet(viewsets.ModelViewSet):
    permission_classes = [IsPlatformAdmin]

    def perform_create(self, serializer):
        instance = serializer.save()
        record_audit(
            request=self.request,
            actor=self.request.user,
            action=f"admin.{instance._meta.model_name}.created",
            target=instance,
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        record_audit(
            request=self.request,
            actor=self.request.user,
            action=f"admin.{instance._meta.model_name}.updated",
            target=instance,
        )


class AdminCityViewSet(AuditedAdminModelViewSet):
    serializer_class = AdminCitySerializer
    queryset = City.objects.all()
    search_fields = ("name",)


class AdminDistrictViewSet(AuditedAdminModelViewSet):
    serializer_class = AdminDistrictSerializer
    queryset = District.objects.select_related("city")
    filterset_fields = ("city", "is_active")
    search_fields = ("name",)


class AdminCategoryViewSet(AuditedAdminModelViewSet):
    serializer_class = AdminCategorySerializer
    queryset = ServiceCategory.objects.select_related("parent")
    filterset_fields = ("parent", "is_active")
    search_fields = ("name",)
