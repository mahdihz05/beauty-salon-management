from django.db import connection
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.serializers import CharField, Serializer
from rest_framework.views import APIView


class HealthCheckResponseSerializer(Serializer):
    status = CharField()
    database = CharField()


class HealthCheckView(APIView):
    """Public liveness check that verifies and identifies the active database."""

    permission_classes = [AllowAny]

    @extend_schema(responses=HealthCheckResponseSerializer)
    def get(self, request):
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return Response({"status": "ok", "database": connection.vendor})
