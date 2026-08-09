from django.http import HttpResponseRedirect
from django.urls import reverse
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView, ListAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from accounts.models import User
from core.audit import record_audit
from salons.views import manageable_branch_ids

from .models import Payment, Settlement, Wallet
from .serializers import (
    PaymentSerializer,
    RecordRemainderPaymentSerializer,
    SettlementProcessSerializer,
    SettlementRequestSerializer,
    SettlementSerializer,
    StartPaymentSerializer,
    WalletSerializer,
)
from .services import (
    confirm_payment,
    process_settlement,
    record_remainder_payment,
    request_settlement,
    start_payment,
)


class PaymentListView(ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = PaymentSerializer
    filterset_fields = ("status", "type", "method", "booking__branch")
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
        if booking.branch_id not in set(manageable_branch_ids(request.user)):
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


class SettlementListCreateView(GenericAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = SettlementRequestSerializer

    def get(self, request):
        queryset = Settlement.objects.select_related("wallet__user")
        if not (request.user.is_superuser or request.user.role == User.Role.ADMIN):
            queryset = queryset.filter(wallet__user=request.user)
        return Response(SettlementSerializer(queryset, many=True).data)

    @extend_schema(request=SettlementRequestSerializer, responses=SettlementSerializer)
    def post(self, request):
        if request.user.role != User.Role.SALON_OWNER and not request.user.is_superuser:
            return Response({"detail": "فقط مالک سالن می‌تواند درخواست تسویه ثبت کند."}, status=403)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        settlement = request_settlement(user=request.user, **serializer.validated_data)
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
