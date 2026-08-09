from django_filters import rest_framework as filters

from .models import Salon


class PublicSalonFilter(filters.FilterSet):
    city = filters.NumberFilter(field_name="branches__city_id")
    district = filters.NumberFilter(field_name="branches__district_id")
    category = filters.NumberFilter(field_name="branches__branch_services__service__category_id")
    min_price = filters.NumberFilter(
        field_name="branches__branch_services__price", lookup_expr="gte"
    )
    max_price = filters.NumberFilter(
        field_name="branches__branch_services__price", lookup_expr="lte"
    )
    featured = filters.BooleanFilter(field_name="is_featured")

    class Meta:
        model = Salon
        fields = ("type", "city", "district", "category", "featured")
