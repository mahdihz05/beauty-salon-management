from django.db.models import Q
from django.utils.text import slugify
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.models import BranchMembership, User
from accounts.permissions import HasBranchAccess
from core.audit import record_audit

from .models import (
    Branch,
    BranchService,
    City,
    District,
    Salon,
    SalonImage,
    Service,
    ServiceCategory,
    Staff,
    StaffService,
    StaffShift,
    StaffTimeOff,
)
from .permissions import IsSalonOwnerOrAdmin
from .serializers import (
    BranchSerializer,
    BranchServiceSerializer,
    CitySerializer,
    DistrictSerializer,
    SalonImageSerializer,
    SalonSerializer,
    ServiceCategorySerializer,
    ServiceSerializer,
    StaffSerializer,
    StaffServiceSerializer,
    StaffShiftSerializer,
    StaffTimeOffSerializer,
)


def accessible_branch_ids(user):
    if not user or not user.is_authenticated:
        return Branch.objects.none().values_list("id", flat=True)
    if user.is_superuser or user.role == User.Role.ADMIN:
        return Branch.objects.values_list("id", flat=True)
    return Branch.objects.filter(
        Q(salon__owner=user) | Q(memberships__user=user, memberships__is_active=True)
    ).values_list("id", flat=True)


def manageable_branch_ids(user, *, include_receptionist=False):
    if not user or not user.is_authenticated:
        return Branch.objects.none().values_list("id", flat=True)
    if user.is_superuser or user.role == User.Role.ADMIN:
        return Branch.objects.values_list("id", flat=True)
    roles = [BranchMembership.Role.MANAGER]
    if include_receptionist:
        roles.append(BranchMembership.Role.RECEPTIONIST)
    return Branch.objects.filter(
        Q(salon__owner=user)
        | Q(memberships__user=user, memberships__is_active=True, memberships__role__in=roles)
    ).values_list("id", flat=True)


class ReadOnlyLocationViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = None
    search_fields = ("name",)


class CityViewSet(ReadOnlyLocationViewSet):
    serializer_class = CitySerializer
    queryset = City.objects.filter(is_active=True)


class DistrictViewSet(ReadOnlyLocationViewSet):
    serializer_class = DistrictSerializer
    queryset = District.objects.filter(is_active=True).select_related("city")
    filterset_fields = ("city",)


class SalonViewSet(viewsets.ModelViewSet):
    serializer_class = SalonSerializer
    permission_classes = [IsAuthenticated, IsSalonOwnerOrAdmin]
    filterset_fields = ("status", "type")
    search_fields = ("name", "description")

    def get_queryset(self):
        user = self.request.user
        queryset = Salon.objects.select_related("owner").prefetch_related("branches", "images")
        if not user.is_authenticated:
            return queryset.none()
        if user.is_superuser or user.role == User.Role.ADMIN:
            return queryset
        return queryset.filter(Q(owner=user) | Q(branches__memberships__user=user)).distinct()

    def perform_create(self, serializer):
        user = self.request.user
        if user.role == User.Role.CUSTOMER:
            user.role = User.Role.SALON_OWNER
            user.save(update_fields=("role",))
        slug = serializer.validated_data.get("slug") or slugify(
            serializer.validated_data["name"], allow_unicode=True
        )
        base_slug = slug or "salon"
        suffix = 2
        while Salon.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{suffix}"
            suffix += 1
        salon = serializer.save(owner=user, status=Salon.Status.DRAFT, slug=slug)
        record_audit(request=self.request, actor=user, action="salon.created", target=salon)

    def perform_update(self, serializer):
        salon = serializer.save()
        record_audit(
            request=self.request, actor=self.request.user, action="salon.updated", target=salon
        )

    @action(detail=True, methods=("post",))
    def submit(self, request, pk=None):
        salon = self.get_object()
        if salon.status not in (Salon.Status.DRAFT, Salon.Status.REJECTED):
            raise ValidationError("این سالن در وضعیت قابل ارسال نیست.")
        if not salon.branches.exists():
            raise ValidationError("پیش از ارسال، حداقل یک شعبه ثبت کنید.")
        salon.status = Salon.Status.PENDING
        salon.rejection_reason = ""
        salon.save(update_fields=("status", "rejection_reason", "updated_at"))
        record_audit(request=request, actor=request.user, action="salon.submitted", target=salon)
        return Response(self.get_serializer(salon).data)


class BranchViewSet(viewsets.ModelViewSet):
    serializer_class = BranchSerializer
    permission_classes = [IsAuthenticated, HasBranchAccess]
    filterset_fields = ("salon", "city", "is_active")
    search_fields = ("name", "address", "phone")

    def get_queryset(self):
        return Branch.objects.filter(
            id__in=accessible_branch_ids(self.request.user)
        ).select_related("salon", "city", "district")

    def perform_create(self, serializer):
        salon = serializer.validated_data["salon"]
        if not (
            self.request.user.is_superuser
            or self.request.user.role == User.Role.ADMIN
            or salon.owner_id == self.request.user.id
        ):
            raise PermissionDenied("فقط مالک سالن می‌تواند شعبه اضافه کند.")
        branch = serializer.save()
        record_audit(
            request=self.request, actor=self.request.user, action="branch.created", target=branch
        )

    def perform_update(self, serializer):
        branch = serializer.save()
        record_audit(
            request=self.request, actor=self.request.user, action="branch.updated", target=branch
        )


class ServiceCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ServiceCategorySerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None
    queryset = ServiceCategory.objects.filter(is_active=True).select_related("parent")


class ServiceViewSet(viewsets.ModelViewSet):
    serializer_class = ServiceSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ("salon", "category", "is_active")
    search_fields = ("name", "description")

    def get_queryset(self):
        user = self.request.user
        queryset = Service.objects.select_related("salon", "category")
        if not user.is_authenticated:
            return queryset.none()
        if user.is_superuser or user.role == User.Role.ADMIN:
            return queryset
        salon_ids = Salon.objects.filter(
            Q(owner=user) | Q(branches__memberships__user=user)
        ).values_list("id", flat=True)
        return queryset.filter(Q(salon__isnull=True) | Q(salon_id__in=salon_ids)).distinct()

    def perform_create(self, serializer):
        salon = serializer.validated_data.get("salon")
        is_admin = self.request.user.is_superuser or self.request.user.role == User.Role.ADMIN
        if (salon is None or salon.owner_id != self.request.user.id) and not is_admin:
            raise PermissionDenied("فقط مالک می‌تواند خدمت اختصاصی سالن ایجاد کند.")
        serializer.save()

    def _ensure_can_manage(self, service):
        is_admin = self.request.user.is_superuser or self.request.user.role == User.Role.ADMIN
        if not is_admin and (
            service.salon_id is None or service.salon.owner_id != self.request.user.id
        ):
            raise PermissionDenied("اجازه ویرایش این خدمت را ندارید.")

    def perform_update(self, serializer):
        self._ensure_can_manage(self.get_object())
        serializer.save()

    def perform_destroy(self, instance):
        self._ensure_can_manage(instance)
        instance.delete()


class BranchScopedViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasBranchAccess]

    def branch_id_from_validated_data(self, serializer):
        branch = serializer.validated_data.get("branch")
        if branch:
            return branch.id
        staff = serializer.validated_data.get("staff")
        if staff:
            return staff.branch_id
        branch_service = serializer.validated_data.get("branch_service")
        if branch_service:
            return branch_service.branch_id
        return None

    def perform_create(self, serializer):
        branch_id = self.branch_id_from_validated_data(serializer)
        if branch_id not in set(manageable_branch_ids(self.request.user)):
            raise PermissionDenied("به این شعبه دسترسی ندارید.")
        instance = serializer.save()
        record_audit(
            request=self.request,
            actor=self.request.user,
            action=f"{instance._meta.model_name}.created",
            target=instance,
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        record_audit(
            request=self.request,
            actor=self.request.user,
            action=f"{instance._meta.model_name}.updated",
            target=instance,
        )

    def perform_destroy(self, instance):
        record_audit(
            request=self.request,
            actor=self.request.user,
            action=f"{instance._meta.model_name}.deleted",
            target=instance,
        )
        instance.delete()


class BranchServiceViewSet(BranchScopedViewSet):
    serializer_class = BranchServiceSerializer
    filterset_fields = ("branch", "service", "is_active")
    search_fields = ("service__name",)

    def get_queryset(self):
        return BranchService.objects.filter(
            branch_id__in=accessible_branch_ids(self.request.user)
        ).select_related("branch", "service", "service__category")


class StaffViewSet(BranchScopedViewSet):
    serializer_class = StaffSerializer
    parser_classes = (JSONParser, FormParser, MultiPartParser)
    filterset_fields = ("branch", "is_active")
    search_fields = ("first_name", "last_name")

    def get_queryset(self):
        return (
            Staff.objects.filter(branch_id__in=accessible_branch_ids(self.request.user))
            .select_related("branch", "user")
            .prefetch_related("shifts", "staff_services__branch_service__service")
        )


class StaffShiftViewSet(BranchScopedViewSet):
    serializer_class = StaffShiftSerializer
    filterset_fields = ("staff", "day_of_week", "is_off")

    def get_queryset(self):
        return StaffShift.objects.filter(
            staff__branch_id__in=accessible_branch_ids(self.request.user)
        ).select_related("staff", "staff__branch")


class StaffServiceViewSet(BranchScopedViewSet):
    serializer_class = StaffServiceSerializer
    filterset_fields = ("staff", "branch_service")

    def get_queryset(self):
        return StaffService.objects.filter(
            staff__branch_id__in=accessible_branch_ids(self.request.user)
        ).select_related("staff", "branch_service", "branch_service__service")


class StaffTimeOffViewSet(BranchScopedViewSet):
    serializer_class = StaffTimeOffSerializer
    filterset_fields = ("staff",)

    def get_queryset(self):
        return StaffTimeOff.objects.filter(
            staff__branch_id__in=accessible_branch_ids(self.request.user)
        ).select_related("staff")


class SalonImageViewSet(
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = SalonImageSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)
    filterset_fields = ("salon",)

    def get_queryset(self):
        queryset = SalonImage.objects.select_related("salon")
        if not self.request.user.is_authenticated:
            return queryset.none()
        if self.request.user.is_superuser or self.request.user.role == User.Role.ADMIN:
            return queryset
        return queryset.filter(salon__owner=self.request.user)

    def perform_create(self, serializer):
        salon = serializer.validated_data["salon"]
        if salon.owner_id != self.request.user.id and not self.request.user.is_superuser:
            raise PermissionDenied("فقط مالک سالن می‌تواند تصویر اضافه کند.")
        image = serializer.save()
        if image.is_cover:
            SalonImage.objects.filter(salon=salon).exclude(pk=image.pk).update(is_cover=False)
        record_audit(
            request=self.request, actor=self.request.user, action="salon.image_added", target=image
        )
