from django.contrib import admin

from .models import (
    Branch,
    BranchService,
    City,
    District,
    Salon,
    SalonImage,
    Service,
    ServiceCategory,
    Staff,
    StaffService,
    StaffShift,
    StaffTimeOff,
)


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ("name", "city", "is_active")
    list_filter = ("city", "is_active")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Salon)
class SalonAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "type", "status", "created_at")
    list_filter = ("type", "status")
    search_fields = ("name", "owner__phone")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ("name", "salon", "city", "phone", "is_active")
    list_filter = ("city", "is_active")
    search_fields = ("name", "salon__name", "phone", "address")


@admin.register(SalonImage)
class SalonImageAdmin(admin.ModelAdmin):
    list_display = ("salon", "alt_text", "is_cover", "sort_order")
    list_filter = ("is_cover",)


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "parent", "is_active", "sort_order")
    list_filter = ("is_active",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "salon", "is_active")
    list_filter = ("category", "is_active")
    search_fields = ("name", "salon__name")


@admin.register(BranchService)
class BranchServiceAdmin(admin.ModelAdmin):
    list_display = ("service", "branch", "price", "duration_minutes", "is_active")
    list_filter = ("price_type", "is_active")
    search_fields = ("service__name", "branch__name")


class StaffShiftInline(admin.TabularInline):
    model = StaffShift
    extra = 0


class StaffServiceInline(admin.TabularInline):
    model = StaffService
    extra = 0


@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ("full_name", "branch", "experience_years", "is_active")
    list_filter = ("branch", "is_active")
    search_fields = ("first_name", "last_name", "branch__name")
    inlines = (StaffShiftInline, StaffServiceInline)


@admin.register(StaffTimeOff)
class StaffTimeOffAdmin(admin.ModelAdmin):
    list_display = ("staff", "starts_at", "ends_at", "reason")
    list_filter = ("starts_at",)
