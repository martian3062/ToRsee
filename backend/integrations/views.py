import hmac

from django.conf import settings
from django.db import connection
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema

from .registry import provider_payload
from .search import SearchService
from .telegram import TelegramCommandRouter


class HealthView(APIView):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        checks = {"database": "ok", "redis": "not_checked"}
        database = {
            "engine": connection.vendor,
            "extensions": [],
        }
        try:
            connection.ensure_connection()
            if connection.vendor == "postgresql":
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT extname
                        FROM pg_extension
                        WHERE extname IN ('postgis', 'timescaledb', 'vector')
                        ORDER BY extname
                        """
                    )
                    database["extensions"] = [row[0] for row in cursor.fetchall()]
        except Exception as exc:
            checks["database"] = f"error: {exc}"
        try:
            import redis
            from django.conf import settings

            redis.from_url(settings.REDIS_URL).ping()
            checks["redis"] = "ok"
        except Exception as exc:
            checks["redis"] = f"error: {exc}"
        return Response(
            {
                "status": "ok",
                "checks": checks,
                "database": database,
                "providers": provider_payload(),
            }
        )


class SearchRequestSerializer(serializers.Serializer):
    query = serializers.CharField(max_length=500)
    top_k = serializers.IntegerField(required=False, min_value=1, max_value=25, default=8)


class SearchView(APIView):
    @extend_schema(request=SearchRequestSerializer, responses=OpenApiTypes.OBJECT)
    def post(self, request):
        serializer = SearchRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(SearchService().search(**serializer.validated_data))


class TelegramWebhookView(APIView):
    authentication_classes = []
    permission_classes = []

    @extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT)
    def post(self, request):
        content_length = int(request.META.get("CONTENT_LENGTH") or 0)
        if content_length > settings.TELEGRAM_WEBHOOK_MAX_BYTES:
            return Response({"detail": "Webhook body is too large."}, status=413)

        if not settings.PROVIDER_MOCK_MODE:
            expected = settings.PROVIDER_SETTINGS["telegram"]["webhook_secret"]
            received = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
            if not expected or not received or not hmac.compare_digest(expected, received):
                return Response({"detail": "Invalid Telegram webhook secret."}, status=403)

        payload = request.data
        response: dict = {"collection": {"outcome": "disabled"}}
        if settings.TELEGRAM_COLLECTION_ENABLED and (
            settings.PROVIDER_MOCK_MODE or settings.INTELLIGENCE_LIVE_ENABLED
        ):
            from drugintel.tasks import ingest_telegram_update_task

            task = ingest_telegram_update_task.delay(payload)
            response["collection"] = {"outcome": "queued", "task_id": task.id}

        message = payload.get("message") or payload.get("edited_message") or {}
        text = (message.get("text") or "").strip()
        if text.startswith("/"):
            response.update(TelegramCommandRouter().handle_update(payload))
        return Response(response)
