from django.contrib import admin

from .models import Payment, Settlement, Wallet, WalletTransaction


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "booking", "amount", "type", "status", "method", "paid_at")
    list_filter = ("status", "type", "method", "provider")
    search_fields = ("gateway_ref", "booking__customer__phone")


class WalletTransactionInline(admin.TabularInline):
    model = WalletTransaction
    extra = 0
    readonly_fields = ("amount", "type", "related_booking", "description", "created_at")


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ("user", "balance", "updated_at")
    search_fields = ("user__phone", "user__name")
    inlines = (WalletTransactionInline,)


@admin.register(Settlement)
class SettlementAdmin(admin.ModelAdmin):
    list_display = ("id", "wallet", "amount", "status", "requested_at", "processed_at")
    list_filter = ("status",)
