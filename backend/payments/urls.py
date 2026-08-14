from django.urls import path

from .views import (
    ConfirmPaymentView,
    MyWalletView,
    PaymentCallbackView,
    PaymentListView,
    ProcessSettlementView,
    RecordRemainderPaymentView,
    SalonFinanceSummaryView,
    SettlementListCreateView,
    StartPaymentView,
    SubmitPaymentView,
    VerifyTransferView,
)

urlpatterns = [
    path("", PaymentListView.as_view(), name="payment-list"),
    path("start/", StartPaymentView.as_view(), name="payment-start"),
    path("submit/", SubmitPaymentView.as_view(), name="payment-submit"),
    path("remainder/", RecordRemainderPaymentView.as_view(), name="payment-remainder"),
    path("<int:pk>/confirm/", ConfirmPaymentView.as_view(), name="payment-confirm"),
    path(
        "<int:pk>/verify-transfer/",
        VerifyTransferView.as_view(),
        name="payment-verify-transfer",
    ),
    path("<int:pk>/callback/", PaymentCallbackView.as_view(), name="payment-callback"),
    path("wallet/", MyWalletView.as_view(), name="my-wallet"),
    path("salons/", SalonFinanceSummaryView.as_view(), name="salon-finance-summary"),
    path("settlements/", SettlementListCreateView.as_view(), name="settlement-list"),
    path(
        "settlements/<int:pk>/process/", ProcessSettlementView.as_view(), name="settlement-process"
    ),
]
