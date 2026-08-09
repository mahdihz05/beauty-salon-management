from django.contrib import admin

from .models import Booking, BookingItem, DiscountCode, DiscountRedemption


class BookingItemInline(admin.TabularInline):
    model = BookingItem
    extra = 0
    readonly_fields = ("branch_service", "staff", "price", "duration_minutes")


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "branch", "staff", "start_at", "status", "total_price")
    list_filter = ("status", "branch", "start_at")
    search_fields = ("customer__phone", "customer__name", "staff__first_name", "staff__last_name")
    inlines = (BookingItemInline,)


@admin.register(DiscountCode)
class DiscountCodeAdmin(admin.ModelAdmin):
    list_display = ("code", "salon", "type", "value", "used_count", "is_active")
    list_filter = ("type", "is_active")
    search_fields = ("code", "salon__name")


@admin.register(DiscountRedemption)
class DiscountRedemptionAdmin(admin.ModelAdmin):
    list_display = ("discount", "booking", "customer", "amount", "created_at")
