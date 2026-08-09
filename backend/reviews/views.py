from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import IsPlatformAdmin
from core.audit import record_audit

from .models import Review
from .serializers import ReviewModerationSerializer, ReviewSerializer
from .services import refresh_salon_rating


class MyReviewViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = (IsAuthenticated,)
    serializer_class = ReviewSerializer
    queryset = Review.objects.none()

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return self.queryset
        return (
            Review.objects.filter(customer=self.request.user)
            .select_related("customer", "salon", "booking__branch")
            .prefetch_related("images")
        )

    def perform_create(self, serializer):
        review = serializer.save()
        record_audit(
            request=self.request,
            actor=self.request.user,
            action="review.created",
            target=review,
            metadata={"booking": review.booking_id},
        )


class PublicReviewViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = (AllowAny,)
    serializer_class = ReviewSerializer

    def get_queryset(self):
        queryset = (
            Review.objects.filter(status=Review.Status.PUBLISHED)
            .select_related("customer", "salon", "booking")
            .prefetch_related("images")
        )
        salon_id = self.request.query_params.get("salon")
        return queryset.filter(salon_id=salon_id) if salon_id else queryset.none()


class ReviewModerationViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = (IsPlatformAdmin,)
    serializer_class = ReviewSerializer
    queryset = Review.objects.select_related("customer", "salon", "booking").prefetch_related(
        "images"
    )
    filterset_fields = ("status", "salon")

    @extend_schema(request=ReviewModerationSerializer, responses=ReviewSerializer)
    @action(detail=True, methods=("post",))
    def moderate(self, request, pk=None):
        review = get_object_or_404(Review.objects.select_related("salon"), pk=pk)
        serializer = ReviewModerationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        previous = review.status
        review.status = serializer.validated_data["status"]
        review.save(update_fields=("status", "updated_at"))
        refresh_salon_rating(review.salon)
        record_audit(
            request=request,
            actor=request.user,
            action="review.moderated",
            target=review,
            metadata={"from": previous, "to": review.status},
        )
        return Response(ReviewSerializer(review, context={"request": request}).data)
