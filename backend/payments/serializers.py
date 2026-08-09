from rest_framework import serializers

from .models import Payment, Settlement, Wallet, WalletTransaction


class StartPaymentSerializer(serializers.Serializer):
    booking = serializers.IntegerField(min_value=1)
    type = serializers.ChoiceField(choices=(Payment.Type.DEPOSIT, Payment.Type.FULL))
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
            "redirect_url",
            "paid_at",
            "created_at",
        )
        read_only_fields = fields

    def get_redirect_url(self, obj) -> str:
        return obj.provider_data.get("redirect_url", "")


class RecordRemainderPaymentSerializer(serializers.Serializer):
    booking = serializers.IntegerField(min_value=1)
    method = serializers.ChoiceField(choices=(Payment.Method.CASH,), default=Payment.Method.CASH)


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
    amount = serializers.IntegerField(min_value=1)
    bank_account = serializers.CharField(max_length=40)


class SettlementProcessSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=(Settlement.Status.PAID, Settlement.Status.REJECTED))
    note = serializers.CharField(required=False, allow_blank=True, max_length=500)
