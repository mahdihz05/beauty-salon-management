import csv
from datetime import timedelta

from django.conf import settings
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.http import HttpResponse
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from bookings.models import Booking, BookingItem
from payments.models import Payment
from salons.views import manageable_branch_ids

from .serializers import ReportQuerySerializer, ReportSummarySerializer


def _report_scope(request, data):
    branch_ids = list(manageable_branch_ids(request.user))
    if not branch_ids:
        from rest_framework.exceptions import PermissionDenied

        raise PermissionDenied("به گزارش‌های مالی دسترسی ندارید.")
    requested = data.get("branch")
    if requested:
        if requested not in branch_ids:
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("به این شعبه دسترسی ندارید.")
        branch_ids = [requested]
    today = timezone.localdate()
    date_to = data.get("date_to", today)
    date_from = data.get("date_from", date_to - timedelta(days=29))
    return branch_ids, date_from, date_to


class ReportSummaryView(GenericAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = ReportQuerySerializer

    @extend_schema(parameters=[ReportQuerySerializer], responses=ReportSummarySerializer)
    def get(self, request):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        branch_ids, date_from, date_to = _report_scope(request, serializer.validated_data)
        bookings = Booking.objects.filter(
            branch_id__in=branch_ids, start_at__date__range=(date_from, date_to)
        )
        payments = Payment.objects.filter(
            booking__branch_id__in=branch_ids,
            status=Payment.Status.PAID,
            paid_at__date__range=(date_from, date_to),
        )
        gross = payments.aggregate(total=Sum("amount"))["total"] or 0
        commission = gross * int(getattr(settings, "PLATFORM_COMMISSION_PERCENT", 10)) // 100
        booking_count = bookings.count()
        daily_booking_rows = {
            row["date"]: row["bookings"]
            for row in bookings.annotate(date=TruncDate("start_at"))
            .values("date")
            .annotate(bookings=Count("id"))
        }
        daily_revenue_rows = {
            row["date"]: row["revenue"]
            for row in payments.annotate(date=TruncDate("paid_at"))
            .values("date")
            .annotate(revenue=Sum("amount"))
        }
        daily = []
        cursor = date_from
        while cursor <= date_to:
            daily.append(
                {
                    "date": cursor,
                    "bookings": daily_booking_rows.get(cursor, 0),
                    "revenue": daily_revenue_rows.get(cursor, 0),
                }
            )
            cursor += timedelta(days=1)
        top_services = list(
            BookingItem.objects.filter(
                booking__branch_id__in=branch_ids,
                booking__start_at__date__range=(date_from, date_to),
                booking__status__in=(Booking.Status.COMPLETED, Booking.Status.NO_SHOW),
            )
            .values(service_name=models_service_name())
            .annotate(count=Count("id"), revenue=Sum("price"))
            .order_by("-count")[:5]
        )
        result = {
            "date_from": date_from,
            "date_to": date_to,
            "gross_revenue": gross,
            "commission": commission,
            "net_revenue": gross - commission,
            "booking_count": booking_count,
            "completed_count": bookings.filter(status=Booking.Status.COMPLETED).count(),
            "cancelled_count": bookings.filter(status=Booking.Status.CANCELLED).count(),
            "no_show_count": bookings.filter(status=Booking.Status.NO_SHOW).count(),
            "average_booking_value": gross // booking_count if booking_count else 0,
            "daily": daily,
            "top_services": top_services,
        }
        return Response(ReportSummarySerializer(result).data)


def models_service_name():
    from django.db.models import F

    return F("branch_service__service__name")


class FinancialCSVView(GenericAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = ReportQuerySerializer

    @extend_schema(parameters=[ReportQuerySerializer], responses={(200, "text/csv"): bytes})
    def get(self, request):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        branch_ids, date_from, date_to = _report_scope(request, serializer.validated_data)
        payments = Payment.objects.filter(
            booking__branch_id__in=branch_ids,
            paid_at__date__range=(date_from, date_to),
        ).select_related("booking__customer", "booking__branch__salon")
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="financial-report.csv"'
        response.write("\ufeff")
        writer = csv.writer(response)
        writer.writerow(["شناسه", "تاریخ", "سالن", "شعبه", "مشتری", "مبلغ", "نوع", "وضعیت"])
        for payment in payments:
            writer.writerow(
                [
                    payment.id,
                    timezone.localtime(payment.paid_at).isoformat() if payment.paid_at else "",
                    payment.booking.branch.salon.name,
                    payment.booking.branch.name,
                    payment.booking.customer.phone,
                    payment.amount,
                    payment.get_type_display(),
                    payment.get_status_display(),
                ]
            )
        return response
