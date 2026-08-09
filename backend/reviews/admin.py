from django.contrib import admin

from .models import Review, ReviewImage


class ReviewImageInline(admin.TabularInline):
    model = ReviewImage
    extra = 0


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("booking", "salon", "overall_rating", "status", "created_at")
    list_filter = ("status", "overall_rating")
    search_fields = ("customer__phone", "salon__name", "comment")
    inlines = (ReviewImageInline,)
