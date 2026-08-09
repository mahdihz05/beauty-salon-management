from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import BranchMembership, CustomerProfile, FavoriteSalon, OTPChallenge, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    ordering = ("-created_at",)
    list_display = ("phone", "name", "role", "is_active", "created_at")
    list_filter = ("role", "is_active", "is_staff")
    search_fields = ("phone", "name")
    fieldsets = (
        (None, {"fields": ("phone", "password")}),
        ("اطلاعات فردی", {"fields": ("name", "role", "phone_verified_at")}),
        (
            "دسترسی‌ها",
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("تاریخ‌ها", {"fields": ("last_login", "date_joined", "created_at")}),
    )
    readonly_fields = ("created_at", "last_login", "date_joined")
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("phone", "name", "role", "password1", "password2"),
            },
        ),
    )


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "email", "gender", "updated_at")
    search_fields = ("user__phone", "user__name", "email")


@admin.register(OTPChallenge)
class OTPChallengeAdmin(admin.ModelAdmin):
    list_display = ("phone", "purpose", "created_at", "expires_at", "consumed_at", "attempts")
    search_fields = ("phone",)
    readonly_fields = ("code_hash", "created_at")


@admin.register(BranchMembership)
class BranchMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "branch", "role", "is_active")
    list_filter = ("role", "is_active")
    search_fields = ("user__phone", "user__name", "branch__name")


@admin.register(FavoriteSalon)
class FavoriteSalonAdmin(admin.ModelAdmin):
    list_display = ("user", "salon", "created_at")
    search_fields = ("user__phone", "salon__name")
