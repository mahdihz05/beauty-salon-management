from django.conf import settings
from django.db.models import Count, Q, Sum
from django.http import HttpResponseRedirect
from django.urls import reverse
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView, ListAPIView, RetrieveAPIView
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from accounts.models import User
from core.audit import record_audit
from salons.views import manageable_branch_ids

from .models import Payment, Settlement, Wallet
from .serializers import (
    PaymentSerializer,
    RecordRemainderPaymentSerializer,
    SalonFinanceSummarySerializer,
    SettlementProcessSerializer,
    SettlementRequestSerializer,
    SettlementSerializer,
    StartPaymentSerializer,
    SubmitPaymentSerializer,
    VerifyTransferSerializer,
    WalletSerializer,
)
from .services import (
    confirm_payment,
    process_settlement,
    record_remainder_payment,
    request_settlement,
    start_payment,
    submit_manual_payment,
    verify_card_transfer,
)


class PaymentListView(ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = PaymentSerializer
    filterset_fields = (
        "status",
        "type",
        "method",
        "booking__branch",
        "booking__branch__salon",
    )
    ordering_fields = ("created_at", "paid_at", "amount")
    ordering = ("-created_at",)

    def get_queryset(self):
        user = self.request.user
        queryset = Payment.objects.select_related("booking__customer", "booking__branch__salon")
        if not user.is_authenticated:
            return queryset.none()
        if user.is_superuser or user.role == User.Role.ADMIN:
            return queryset
        branch_ids = manageable_branch_ids(user)
        if branch_ids:
            return queryset.filter(booking__branch_id__in=branch_ids)
        return queryset.filter(booking__customer=user)


class StartPaymentView(GenericAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = StartPaymentSerializer

    @extend_schema(request=StartPaymentSerializer, responses=PaymentSerializer)
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        callback_url = request.build_absolute_uri(reverse("payment-callback", args=(0,))).replace(
            "/0/", "/{payment_id}/"
        )
        payment = start_payment(
            customer=request.user,
            booking_id=serializer.validated_data["booking"],
            payment_type=serializer.validated_data["type"],
            callback_url=callback_url,
            discount_code=serializer.validated_data.get("discount_code", ""),
        )
        record_audit(
            request=request,
            actor=request.user,
            action="payment.started",
            target=payment,
            metadata={"amount": payment.amount, "type": payment.type},
        )
        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)


class SubmitPaymentView(GenericAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = SubmitPaymentSerializer
    parser_classes = (JSONParser, FormParser, MultiPartParser)

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payment = submit_manual_payment(
            customer=request.user,
            booking_id=serializer.validated_data["booking"],
            payment_type=serializer.validated_data["type"],
            method=serializer.validated_data["method"],
            tracking_code=serializer.validated_data.get("tracking_code", ""),
            receipt=serializer.validated_data.get("receipt"),
            discount_code=serializer.validated_data.get("discount_code", ""),
        )
        record_audit(
            request=request,
            actor=request.user,
            action="payment.submitted",
            target=payment,
            metadata={"method": payment.method, "booking": payment.booking_id},
        )
        return Response(
            PaymentSerializer(payment, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class VerifyTransferView(GenericAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = VerifyTransferSerializer

    def post(self, request, pk):
        try:
            payment = Payment.objects.select_related("booking__branch").get(pk=pk)
        except Payment.DoesNotExist:
            return Response({"detail": "پرداخت پیدا نشد."}, status=404)
        if payment.booking.branch_id not in set(manageable_branch_ids(request.user)):
            return Response({"detail": "اجازه بررسی این رسید را ندارید."}, status=403)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payment = verify_card_transfer(
            payment_id=pk,
            verifier=request.user,
            next_status=serializer.validated_data["status"],
        )
        record_audit(
            request=request,
            actor=request.user,
            action="payment.transfer_verified",
            target=payment,
            metadata={"status": payment.status},
        )
        return Response(PaymentSerializer(payment, context={"request": request}).data)


class ConfirmPaymentView(GenericAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = PaymentSerializer
    queryset = Payment.objects.all()

    @extend_schema(request=None, responses=PaymentSerializer)
    def post(self, request, pk):
        payment = confirm_payment(customer=request.user, payment_id=pk)
        record_audit(
            request=request,
            actor=request.user,
            action="payment.confirmed",
            target=payment,
            metadata={"amount": payment.amount, "booking": payment.booking_id},
        )
        return Response(PaymentSerializer(payment).data)


class PaymentCallbackView(GenericAPIView):
    permission_classes = (AllowAny,)
    serializer_class = PaymentSerializer
    queryset = Payment.objects.all()

    @extend_schema(request=None, responses={302: None})
    def get(self, request, pk):
        return self._confirm(request, pk)

    @extend_schema(request=None, responses={302: None})
    def post(self, request, pk):
        return self._confirm(request, pk)

    def _confirm(self, request, pk):
        payment = confirm_payment(payment_id=pk)
        record_audit(
            request=request,
            actor=payment.booking.customer,
            action="payment.callback_confirmed",
            target=payment,
            metadata={"amount": payment.amount, "booking": payment.booking_id},
        )
        return HttpResponseRedirect(f"/booking/success/{payment.booking_id}")


class RecordRemainderPaymentView(GenericAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = RecordRemainderPaymentSerializer

    @extend_schema(request=RecordRemainderPaymentSerializer, responses=PaymentSerializer)
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking_id = serializer.validated_data["booking"]
        from bookings.models import Booking

        try:
            booking = Booking.objects.select_related("branch").get(pk=booking_id)
        except Booking.DoesNotExist:
            return Response({"detail": "رزرو پیدا نشد."}, status=404)
        if booking.branch_id not in set(
            manageable_branch_ids(request.user, include_receptionist=True)
        ):
            return Response({"detail": "اجازه ثبت پرداخت این شعبه را ندارید."}, status=403)
        payment = record_remainder_payment(
            booking_id=booking_id, method=serializer.validated_data["method"]
        )
        record_audit(
            request=request,
            actor=request.user,
            action="payment.remainder_recorded",
            target=payment,
            metadata={"booking": booking_id, "amount": payment.amount},
        )
        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)


class MyWalletView(RetrieveAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = WalletSerializer

    def get_object(self):
        wallet, _ = Wallet.objects.get_or_create(user=self.request.user)
        return Wallet.objects.prefetch_related("transactions").get(pk=wallet.pk)


class SalonFinanceSummaryView(GenericAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = SalonFinanceSummarySerializer

    def get(self, request):
        from salons.models import Salon

        salons = Salon.objects.all()
        if not (request.user.is_superuser or request.user.role == User.Role.ADMIN):
            if request.user.role == User.Role.SALON_OWNER:
                salons = salons.filter(owner=request.user)
            else:
                salons = salons.filter(
                    branches__id__in=manageable_branch_ids(request.user)
                ).distinct()
        salon_rows = list(
            salons.annotate(branch_count=Count("branches", distinct=True)).values(
                "id", "name", "branch_count"
            )
        )
        ids = [row["id"] for row in salon_rows]
        payment_rows = {
            row["booking__branch__salon_id"]: row
            for row in Payment.objects.filter(booking__branch__salon_id__in=ids)
            .values("booking__branch__salon_id")
            .annotate(
                paid=Sum("amount", filter=Q(status=Payment.Status.PAID)),
                refunded=Sum("amount", filter=Q(status=Payment.Status.REFUNDED)),
                payment_count=Count("id"),
            )
        }
        settlement_rows = {
            row["salon_id"]: row
            for row in Settlement.objects.filter(salon_id__in=ids)
            .values("salon_id")
            .annotate(
                settled=Sum("amount", filter=Q(status=Settlement.Status.PAID)),
                requested=Sum("amount", filter=Q(status=Settlement.Status.REQUESTED)),
            )
        }
        commission_percent = int(getattr(settings, "PLATFORM_COMMISSION_PERCENT", 10))
        result = []
        for salon in salon_rows:
            payment = payment_rows.get(salon["id"], {})
            settlement = settlement_rows.get(salon["id"], {})
            gross = payment.get("paid") or 0
            commission = gross * commission_percent // 100
            result.append(
                {
                    **salon,
                    "gross_revenue": gross,
                    "refunded_amount": payment.get("refunded") or 0,
                    "commission": commission,
                    "net_revenue": gross - commission,
                    "settled_amount": settlement.get("settled") or 0,
                    "requested_amount": settlement.get("requested") or 0,
                    "payment_count": payment.get("payment_count") or 0,
                }
            )
        return Response(self.get_serializer(result, many=True).data)


class SettlementListCreateView(GenericAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = SettlementRequestSerializer

    def get(self, request):
        queryset = Settlement.objects.select_related("wallet__user", "salon")
        if not (request.user.is_superuser or request.user.role == User.Role.ADMIN):
            queryset = queryset.filter(wallet__user=request.user)
        salon_id = request.query_params.get("salon")
        if salon_id:
            queryset = queryset.filter(salon_id=salon_id)
        return Response(SettlementSerializer(queryset, many=True).data)

    @extend_schema(request=SettlementRequestSerializer, responses=SettlementSerializer)
    def post(self, request):
        if request.user.role != User.Role.SALON_OWNER and not request.user.is_superuser:
            return Response({"detail": "فقط مالک سالن می‌تواند درخواست تسویه ثبت کند."}, status=403)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        from salons.models import Salon

        data = dict(serializer.validated_data)
        salon_id = data.pop("salon", None)
        owned_salons = Salon.objects.filter(owner=request.user)
        if salon_id is None and owned_salons.count() == 1:
            salon_id = owned_salons.values_list("id", flat=True).first()
        try:
            salon = owned_salons.get(pk=salon_id)
        except Salon.DoesNotExist:
            return Response({"detail": "سالن معتبر نیست یا متعلق به شما نیست."}, status=403)
        settlement = request_settlement(user=request.user, salon=salon, **data)
        record_audit(
            request=request,
            actor=request.user,
            action="settlement.requested",
            target=settlement,
            metadata={"amount": settlement.amount},
        )
        return Response(SettlementSerializer(settlement).data, status=status.HTTP_201_CREATED)


class ProcessSettlementView(GenericAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = SettlementProcessSerializer

    @extend_schema(request=SettlementProcessSerializer, responses=SettlementSerializer)
    def post(self, request, pk):
        if not (request.user.is_superuser or request.user.role == User.Role.ADMIN):
            return Response({"detail": "اجازه پردازش تسویه را ندارید."}, status=403)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        settlement = process_settlement(
            settlement_id=pk,
            next_status=serializer.validated_data["status"],
            note=serializer.validated_data.get("note", ""),
        )
        record_audit(
            request=request,
            actor=request.user,
            action="settlement.processed",
            target=settlement,
            metadata={"status": settlement.status, "amount": settlement.amount},
        )
        return Response(SettlementSerializer(settlement).data)
