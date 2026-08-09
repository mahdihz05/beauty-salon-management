from django.urls import path

from .views import FinancialCSVView, ReportSummaryView

urlpatterns = [
    path("summary/", ReportSummaryView.as_view(), name="report-summary"),
    path("financial.csv", FinancialCSVView.as_view(), name="report-financial-csv"),
]
