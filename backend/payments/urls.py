from django.urls import path

from .views import (
    ConfirmPaymentView,
    MyWalletView,
    PaymentCallbackView,
    PaymentListView,
    ProcessSettlementView,
    RecordRemainderPaymentView,
    SettlementListCreateView,
    StartPaymentView,
)

urlpatterns = [
    path("", PaymentListView.as_view(), name="payment-list"),
    path("start/", StartPaymentView.as_view(), name="payment-start"),
    path("remainder/", RecordRemainderPaymentView.as_view(), name="payment-remainder"),
    path("<int:pk>/confirm/", ConfirmPaymentView.as_view(), name="payment-confirm"),
    path("<int:pk>/callback/", PaymentCallbackView.as_view(), name="payment-callback"),
    path("wallet/", MyWalletView.as_view(), name="my-wallet"),
    path("settlements/", SettlementListCreateView.as_view(), name="settlement-list"),
    path(
        "settlements/<int:pk>/process/", ProcessSettlementView.as_view(), name="settlement-process"
    ),
]
