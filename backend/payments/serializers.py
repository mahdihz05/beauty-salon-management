from rest_framework import serializers

from .models import Payment, Settlement, Wallet, WalletTransaction

PAYMENT_SELECTION_CHOICES = (
    (Payment.Type.DEPOSIT, "بیعانه"),
    (Payment.Type.FULL, "پرداخت کامل"),
)


class StartPaymentSerializer(serializers.Serializer):
    booking = serializers.IntegerField(min_value=1)
    type = serializers.ChoiceField(choices=PAYMENT_SELECTION_CHOICES)
    discount_code = serializers.CharField(required=False, allow_blank=True, max_length=32)


class PaymentSerializer(serializers.ModelSerializer):
    redirect_url = serializers.SerializerMethodField()
    customer_phone = serializers.CharField(source="booking.customer.phone", read_only=True)
    salon_name = serializers.CharField(source="booking.branch.salon.name", read_only=True)
    branch_name = serializers.CharField(source="booking.branch.name", read_only=True)

    class Meta:
        model = Payment
        fields = (
            "id",
            "booking",
            "customer_phone",
            "salon_name",
            "branch_name",
            "amount",
            "type",
            "status",
            "method",
            "provider",
            "gateway_ref",
            "tracking_code",
            "receipt",
            "verified_by",
            "verified_at",
            "redirect_url",
            "paid_at",
            "created_at",
        )
        read_only_fields = fields

    def get_redirect_url(self, obj) -> str:
        return obj.provider_data.get("redirect_url", "")


class RecordRemainderPaymentSerializer(serializers.Serializer):
    booking = serializers.IntegerField(min_value=1)
    method = serializers.ChoiceField(
        choices=(Payment.Method.IN_PERSON, Payment.Method.CASH), default=Payment.Method.IN_PERSON
    )

    def validate_method(self, value):
        return Payment.Method.IN_PERSON


class SubmitPaymentSerializer(serializers.Serializer):
    booking = serializers.IntegerField(min_value=1)
    type = serializers.ChoiceField(choices=PAYMENT_SELECTION_CHOICES)
    method = serializers.ChoiceField(
        choices=(Payment.Method.IN_PERSON, Payment.Method.CARD_TO_CARD)
    )
    tracking_code = serializers.CharField(required=False, allow_blank=True, max_length=80)
    receipt = serializers.ImageField(required=False, allow_null=True)
    discount_code = serializers.CharField(required=False, allow_blank=True, max_length=32)

    def validate(self, attrs):
        if (
            attrs["method"] == Payment.Method.CARD_TO_CARD
            and not attrs.get("tracking_code")
            and not attrs.get("receipt")
        ):
            raise serializers.ValidationError(
                "برای کارت‌به‌کارت، تصویر رسید یا کد پیگیری الزامی است."
            )
        return attrs


class VerifyTransferSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=(Payment.Status.PAID, Payment.Status.FAILED))


class SalonFinanceSummarySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    branch_count = serializers.IntegerField()
    gross_revenue = serializers.IntegerField()
    refunded_amount = serializers.IntegerField()
    commission = serializers.IntegerField()
    net_revenue = serializers.IntegerField()
    settled_amount = serializers.IntegerField()
    requested_amount = serializers.IntegerField()
    payment_count = serializers.IntegerField()


class WalletTransactionSerializer(serializers.ModelSerializer):
    type_label = serializers.CharField(source="get_type_display", read_only=True)

    class Meta:
        model = WalletTransaction
        fields = (
            "id",
            "amount",
            "type",
            "type_label",
            "related_booking",
            "description",
            "created_at",
        )


class WalletSerializer(serializers.ModelSerializer):
    transactions = WalletTransactionSerializer(many=True, read_only=True)

    class Meta:
        model = Wallet
        fields = ("balance", "updated_at", "transactions")


class SettlementSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source="wallet.user.name", read_only=True)
    owner_phone = serializers.CharField(source="wallet.user.phone", read_only=True)

    class Meta:
        model = Settlement
        fields = (
            "id",
            "amount",
            "salon",
            "status",
            "bank_account",
            "note",
            "owner_name",
            "owner_phone",
            "requested_at",
            "processed_at",
        )
        read_only_fields = (
            "id",
            "status",
            "note",
            "owner_name",
            "owner_phone",
            "requested_at",
            "processed_at",
        )


class SettlementRequestSerializer(serializers.Serializer):
    salon = serializers.IntegerField(required=False, min_value=1)
    amount = serializers.IntegerField(min_value=1)
    bank_account = serializers.CharField(max_length=40)


class SettlementProcessSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=(Settlement.Status.PAID, Settlement.Status.REJECTED))
    note = serializers.CharField(required=False, allow_blank=True, max_length=500)
