import csv

from django.conf import settings
from django.db.models import Count, Q, Sum
from django.http import HttpResponse, HttpResponseRedirect
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


def finance_branch_ids(user):
    from salons.models import Branch

    if user.is_superuser or user.role == User.Role.ADMIN:
        return Branch.objects.values_list("id", flat=True)
    return manageable_branch_ids(user)


def filter_payments(request, queryset=None):
    if queryset is None:
        queryset = Payment.objects.all()
    queryset = queryset.filter(booking__branch_id__in=finance_branch_ids(request.user))
    params = request.query_params
    filters = {
        "status": "status",
        "type": "type",
        "method": "method",
        "branch": "booking__branch_id",
        "salon": "booking__branch__salon_id",
        "source": "booking__source",
    }
    for param, field in filters.items():
        if params.get(param):
            queryset = queryset.filter(**{field: params[param]})
    if params.get("date_from"):
        queryset = queryset.filter(created_at__date__gte=params["date_from"])
    if params.get("date_to"):
        queryset = queryset.filter(created_at__date__lte=params["date_to"])
    if params.get("search"):
        term = params["search"]
        lookup = Q(booking__customer__phone__icontains=term) | Q(
            booking__customer__name__icontains=term
        )
        if term.isdigit():
            lookup |= Q(booking_id=int(term))
        queryset = queryset.filter(lookup)
    return queryset


class PaymentListView(ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = PaymentSerializer
    ordering_fields = ("created_at", "paid_at", "amount")
    ordering = ("-created_at",)

    def get_queryset(self):
        user = self.request.user
        queryset = Payment.objects.select_related("booking__customer", "booking__branch__salon")
        if not user.is_authenticated:
            return queryset.none()
        if user.role == User.Role.CUSTOMER:
            return queryset.filter(booking__customer=user)
        return filter_payments(self.request, queryset)


class StartPaymentView(GenericAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = StartPaymentSerializer

    @extend_schema(request=StartPaymentSerializer, responses=PaymentSerializer)
    def post(self, request):
        if not getattr(settings, "ENABLE_LEGACY_PAYMENT_ENDPOINTS", False):
            return Response(
                {"detail": "در رزرو جدید فقط پرداخت حضوری یا کارت‌به‌کارت قابل انتخاب است."},
                status=status.HTTP_410_GONE,
            )
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

    @extend_schema(operation_id="finance_salon_list")
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
        allowed_branches = set(finance_branch_ids(request.user))
        salon_rows = list(
            salons.annotate(
                branch_count=Count(
                    "branches", filter=Q(branches__id__in=allowed_branches), distinct=True
                )
            ).values("id", "name", "branch_count")
        )
        ids = [row["id"] for row in salon_rows]
        payment_rows = {
            row["booking__branch__salon_id"]: row
            for row in Payment.objects.filter(
                booking__branch__salon_id__in=ids, booking__branch_id__in=allowed_branches
            )
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
        page = self.paginate_queryset(result)
        if page is not None:
            return self.get_paginated_response(self.get_serializer(page, many=True).data)
        return Response(self.get_serializer(result, many=True).data)


class SalonFinanceDetailView(GenericAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = SalonFinanceSummarySerializer

    @extend_schema(operation_id="finance_salon_detail")
    def get(self, request, salon_id):
        from salons.models import Branch, Salon

        allowed = set(finance_branch_ids(request.user))
        try:
            salon = Salon.objects.get(pk=salon_id, branches__id__in=allowed)
        except Salon.DoesNotExist:
            return Response({"detail": "اطلاعات مالی سالن در دسترس نیست."}, status=404)
        branches = Branch.objects.filter(salon=salon, id__in=allowed)
        payments = filter_payments(request, Payment.objects.filter(booking__branch__salon=salon))
        commission_percent = int(getattr(settings, "PLATFORM_COMMISSION_PERCENT", 10))
        summaries = []
        for branch in branches:
            aggregate = payments.filter(booking__branch=branch).aggregate(
                gross=Sum("amount", filter=Q(status=Payment.Status.PAID)),
                refunded=Sum("amount", filter=Q(status=Payment.Status.REFUNDED)),
                count=Count("id"),
            )
            gross = aggregate["gross"] or 0
            refunded = aggregate["refunded"] or 0
            commission = gross * commission_percent // 100
            summaries.append(
                {
                    "id": branch.id,
                    "name": branch.name,
                    "payment_count": aggregate["count"],
                    "gross_revenue": gross,
                    "refunded_amount": refunded,
                    "commission": commission,
                    "net_revenue": gross - commission - refunded,
                }
            )
        totals = {
            key: sum(row[key] for row in summaries)
            for key in (
                "payment_count",
                "gross_revenue",
                "refunded_amount",
                "commission",
                "net_revenue",
            )
        }
        can_see_settlements = request.user.is_superuser or request.user.role in (
            User.Role.ADMIN,
            User.Role.SALON_OWNER,
        )
        settlements = (
            Settlement.objects.filter(salon=salon)
            if can_see_settlements
            else Settlement.objects.none()
        )
        return Response(
            {
                "id": salon.id,
                "name": salon.name,
                "totals": totals,
                "branches": summaries,
                "settlements": SettlementSerializer(settlements, many=True).data,
            }
        )


class FinanceCsvView(GenericAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = PaymentSerializer

    def get(self, request):
        payments = filter_payments(
            request,
            Payment.objects.select_related("booking__customer", "booking__branch__salon"),
        ).order_by("-created_at")
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="finance.csv"'
        response.write("\ufeff")
        writer = csv.writer(response)
        writer.writerow(
            [
                "payment_id",
                "booking_id",
                "salon",
                "branch",
                "customer",
                "amount",
                "method",
                "status",
                "source",
                "created_at",
            ]
        )
        for payment in payments.iterator():
            writer.writerow(
                [
                    payment.id,
                    payment.booking_id,
                    payment.booking.branch.salon.name,
                    payment.booking.branch.name,
                    payment.booking.customer.phone,
                    payment.amount,
                    payment.method,
                    payment.status,
                    payment.booking.source,
                    payment.created_at.isoformat(),
                ]
            )
        return response


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
        page = self.paginate_queryset(queryset)
        if page is not None:
            return self.get_paginated_response(SettlementSerializer(page, many=True).data)
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
