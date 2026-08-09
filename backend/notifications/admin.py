from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("event", "recipient", "booking", "status", "sent_at")
    list_filter = ("event", "status", "channel")
    search_fields = ("recipient__phone", "message", "provider_ref")
