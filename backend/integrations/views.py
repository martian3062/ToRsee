from django.db import connection
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from .registry import provider_payload
from .search import SearchService
from .telegram import TelegramCommandRouter


class HealthView(APIView):
    def get(self, request):
        checks = {"database": "ok", "redis": "not_checked"}
        try:
            connection.ensure_connection()
        except Exception as exc:
            checks["database"] = f"error: {exc}"
        try:
            import redis
            from django.conf import settings

            redis.from_url(settings.REDIS_URL).ping()
            checks["redis"] = "ok"
        except Exception as exc:
            checks["redis"] = f"error: {exc}"
        return Response({"status": "ok", "checks": checks, "providers": provider_payload()})


class SearchRequestSerializer(serializers.Serializer):
    query = serializers.CharField(max_length=500)
    top_k = serializers.IntegerField(required=False, min_value=1, max_value=25, default=8)


class SearchView(APIView):
    def post(self, request):
        serializer = SearchRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(SearchService().search(**serializer.validated_data))


class TelegramWebhookView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        return Response(TelegramCommandRouter().handle_update(request.data))
