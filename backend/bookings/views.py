from django.db.models import BigIntegerField, Count, Max, Q, Sum
from django.db.models.functions import Coalesce
from django_filters import rest_framework as filters
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from accounts.models import CustomerProfile, User
from accounts.utils import normalize_iranian_phone
from core.audit import record_audit
from salons.views import accessible_branch_ids, manageable_branch_ids

from .engine import create_booking_hold, get_available_slots
from .models import Booking, DiscountCode
from .serializers import (
    AvailabilityQuerySerializer,
    AvailableSlotSerializer,
    BookingSerializer,
    CreateHoldSerializer,
    CreateManualBookingSerializer,
    CustomerSummarySerializer,
    DiscountCodeSerializer,
)


class AvailabilityView(GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = AvailabilityQuerySerializer
    queryset = Booking.objects.none()

    @extend_schema(
        parameters=[AvailabilityQuerySerializer], responses=AvailableSlotSerializer(many=True)
    )
    def get(self, request):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        slots = get_available_slots(
            branch=data["branch"],
            service_ids=data["services"],
            target_date=data["date"],
            staff_id=data.get("staff"),
        )
        return Response(AvailableSlotSerializer(slots, many=True).data)


class CreateHoldView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CreateHoldSerializer

    @extend_schema(request=CreateHoldSerializer, responses=BookingSerializer)
    def post(self, request):
        if request.user.role != User.Role.CUSTOMER:
            return Response({"detail": "رزرو آنلاین فقط از حساب مشتری امکان‌پذیر است."}, status=403)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking = create_booking_hold(
            customer=request.user,
            source=Booking.Source.ONLINE,
            **serializer.validated_data,
        )
        record_audit(
            request=request,
            actor=request.user,
            action="booking.hold_created",
            target=booking,
            metadata={"expires_at": booking.hold_expires_at.isoformat()},
        )
        return Response(
            BookingSerializer(booking, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class CreateManualBookingView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CreateManualBookingSerializer

    @extend_schema(request=CreateManualBookingSerializer, responses=BookingSerializer)
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        branch = data["branch"]
        if branch.id not in set(manageable_branch_ids(request.user, include_receptionist=True)):
            return Response({"detail": "اجازه ثبت نوبت در این شعبه را ندارید."}, status=403)

        phone = normalize_iranian_phone(data.pop("customer_phone"))
        customer_name = data.pop("customer_name", "")
        customer, created = User.objects.get_or_create(
            phone=phone,
            defaults={"name": customer_name, "role": User.Role.CUSTOMER},
        )
        if customer_name and not customer.name:
            customer.name = customer_name
            customer.save(update_fields=("name",))
        CustomerProfile.objects.get_or_create(user=customer)
        booking = create_booking_hold(customer=customer, source=Booking.Source.WALK_IN, **data)
        booking.status = Booking.Status.CONFIRMED
        booking.hold_expires_at = None
        booking.save(update_fields=("status", "hold_expires_at", "updated_at"))

        from notifications.models import Notification
        from notifications.services import send_booking_notification

        send_booking_notification(booking=booking, event=Notification.Event.BOOKING_CONFIRMED)
        record_audit(
            request=request,
            actor=request.user,
            action="booking.manual_created",
            target=booking,
            metadata={"customer_created": created, "branch": branch.id},
        )
        return Response(
            BookingSerializer(booking, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class BookingFilter(filters.FilterSet):
    start_date = filters.DateFilter(field_name="start_at", lookup_expr="date__gte")
    end_date = filters.DateFilter(
        field_name="start_at", lookup_expr="date", method="filter_end_date"
    )

    def filter_end_date(self, queryset, _name, value):
        return queryset.filter(start_at__date__lte=value)

    class Meta:
        model = Booking
        fields = ("branch", "staff", "status", "source", "start_date", "end_date")


class BookingViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated]
    filterset_class = BookingFilter
    ordering_fields = ("start_at", "created_at")
    search_fields = ("customer__phone", "customer__name", "staff__first_name", "staff__last_name")

    def get_queryset(self):
        user = self.request.user
        queryset = Booking.objects.select_related(
            "customer", "branch", "branch__salon", "staff"
        ).prefetch_related("items__branch_service__service", "items__staff", "payments")
        if not user.is_authenticated:
            return queryset.none()
        if user.is_superuser or user.role == User.Role.ADMIN:
            return queryset
        branch_ids = accessible_branch_ids(user)
        if user.role == User.Role.STAFF:
            return queryset.filter(Q(customer=user) | Q(staff__user=user)).distinct()
        return queryset.filter(Q(customer=user) | Q(branch_id__in=branch_ids)).distinct()

    def _can_manage(self, booking):
        user = self.request.user
        return bool(
            user.role in (User.Role.SALON_OWNER, User.Role.BRANCH_MANAGER)
            and booking.branch_id in set(manageable_branch_ids(user))
        )

    def _can_check_in(self, booking):
        user = self.request.user
        return bool(
            user.role
            in (
                User.Role.SALON_OWNER,
                User.Role.BRANCH_MANAGER,
                User.Role.RECEPTIONIST,
            )
            and booking.branch_id in set(manageable_branch_ids(user, include_receptionist=True))
        )

    @action(detail=True, methods=("post",))
    def cancel(self, request, pk=None):
        booking = self.get_object()
        if booking.customer_id != request.user.id and not self._can_manage(booking):
            return Response({"detail": "اجازه لغو این رزرو را ندارید."}, status=403)
        from payments.services import cancel_booking_with_policy

        booking, refund_amount = cancel_booking_with_policy(
            booking_id=booking.pk,
            reason=request.data.get("reason", "لغو توسط کاربر"),
        )
        record_audit(
            request=request,
            actor=request.user,
            action="booking.cancelled",
            target=booking,
            metadata={"refund_amount": refund_amount},
        )
        response_data = self.get_serializer(booking).data
        response_data["refund_amount"] = refund_amount
        response_data["refund_destination"] = "wallet" if refund_amount else None
        return Response(response_data)

    @action(detail=True, methods=("post",), url_path="check-in")
    def check_in(self, request, pk=None):
        booking = self.get_object()
        if not self._can_check_in(booking):
            return Response({"detail": "اجازه پذیرش این نوبت را ندارید."}, status=403)
        if booking.status != Booking.Status.CONFIRMED:
            return Response({"detail": "فقط نوبت تأییدشده قابل پذیرش است."}, status=400)
        if request.user.role == User.Role.RECEPTIONIST and booking.source != Booking.Source.ONLINE:
            return Response({"detail": "پذیرش فقط برای نوبت‌های آنلاین قابل ثبت است."}, status=400)
        if booking.checked_in_at is None:
            from django.utils import timezone

            booking.checked_in_at = timezone.now()
            booking.checked_in_by = request.user
            booking.save(update_fields=("checked_in_at", "checked_in_by", "updated_at"))
            record_audit(
                request=request,
                actor=request.user,
                action="booking.checked_in",
                target=booking,
            )
        return Response(self.get_serializer(booking).data)

    @action(detail=True, methods=("post",), url_path="set-status")
    def set_status(self, request, pk=None):
        booking = self.get_object()
        if not self._can_manage(booking):
            return Response({"detail": "اجازه تغییر وضعیت را ندارید."}, status=403)
        next_status = request.data.get("status")
        allowed = {
            Booking.Status.CONFIRMED,
            Booking.Status.COMPLETED,
            Booking.Status.NO_SHOW,
            Booking.Status.CANCELLED,
        }
        if next_status not in allowed:
            return Response({"detail": "وضعیت انتخاب‌شده معتبر نیست."}, status=400)
        previous = booking.status
        transitions = {
            Booking.Status.PENDING_PAYMENT: {Booking.Status.CANCELLED},
            Booking.Status.CONFIRMED: {
                Booking.Status.COMPLETED,
                Booking.Status.NO_SHOW,
                Booking.Status.CANCELLED,
            },
        }
        if next_status not in transitions.get(previous, set()):
            return Response({"detail": "تغییر وضعیت درخواستی مجاز نیست."}, status=400)
        if next_status == Booking.Status.COMPLETED:
            paid_amount = (
                booking.payments.filter(status="paid").aggregate(total=Sum("amount"))["total"] or 0
            )
            if paid_amount < booking.total_price:
                return Response(
                    {"detail": "پیش از تکمیل خدمت، مانده پرداخت را ثبت کنید."}, status=400
                )
        if next_status == Booking.Status.CANCELLED:
            from payments.services import cancel_booking_with_policy

            booking, refund_amount = cancel_booking_with_policy(
                booking_id=booking.pk,
                reason=request.data.get("reason", "لغو توسط سالن"),
            )
        else:
            booking.status = next_status
            booking.save(update_fields=("status", "updated_at"))
            from payments.services import credit_salon_for_booking

            credited_amount = credit_salon_for_booking(booking_id=booking.pk)
        record_audit(
            request=request,
            actor=request.user,
            action="booking.status_changed",
            target=booking,
            metadata={
                "from": previous,
                "to": next_status,
                "refund_amount": locals().get("refund_amount", 0),
                "credited_amount": locals().get("credited_amount", 0),
            },
        )
        return Response(self.get_serializer(booking).data)


class DiscountCodeViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)
    serializer_class = DiscountCodeSerializer
    filterset_fields = ("salon", "is_active", "type")
    search_fields = ("code", "salon__name")

    def get_queryset(self):
        queryset = DiscountCode.objects.select_related("salon")
        user = self.request.user
        if not user.is_authenticated:
            return queryset.none()
        if user.is_superuser or user.role == User.Role.ADMIN:
            return queryset
        return queryset.filter(salon__owner=user)

    def perform_create(self, serializer):
        discount = serializer.save()
        record_audit(
            request=self.request,
            actor=self.request.user,
            action="discount.created",
            target=discount,
        )

    def perform_update(self, serializer):
        discount = serializer.save()
        record_audit(
            request=self.request,
            actor=self.request.user,
            action="discount.updated",
            target=discount,
        )


class CustomerViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = (IsAuthenticated,)
    serializer_class = CustomerSummarySerializer
    search_fields = ("name", "phone")
    ordering_fields = ("last_booking_at", "total_spent", "booking_count")
    ordering = ("-last_booking_at",)

    def get_queryset(self):
        branch_ids = manageable_branch_ids(self.request.user)
        return (
            User.objects.filter(bookings__branch_id__in=branch_ids)
            .annotate(
                booking_count=Count(
                    "bookings", filter=Q(bookings__branch_id__in=branch_ids), distinct=True
                ),
                total_spent=Coalesce(
                    Sum(
                        "bookings__payments__amount",
                        filter=Q(
                            bookings__branch_id__in=branch_ids,
                            bookings__payments__status="paid",
                        ),
                    ),
                    0,
                    output_field=BigIntegerField(),
                ),
                last_booking_at=Max(
                    "bookings__start_at", filter=Q(bookings__branch_id__in=branch_ids)
                ),
            )
            .distinct()
        )
