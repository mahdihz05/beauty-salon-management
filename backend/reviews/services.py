from django.db.models import Avg, Count

from .models import Review


def refresh_salon_rating(salon) -> None:
    summary = Review.objects.filter(salon=salon, status=Review.Status.PUBLISHED).aggregate(
        average=Avg("overall_rating"), count=Count("id")
    )
    salon.rating_average = round(summary["average"] or 0, 2)
    salon.review_count = summary["count"]
    salon.save(update_fields=("rating_average", "review_count", "updated_at"))
