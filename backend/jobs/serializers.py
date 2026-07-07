from rest_framework import serializers

from sources.serializers import DocumentSerializer

from .models import IngestionJob, JobTarget


class JobTargetSerializer(serializers.ModelSerializer):
    document = DocumentSerializer(read_only=True)

    class Meta:
        model = JobTarget
        fields = [
            "id",
            "url",
            "status",
            "fetched_with",
            "document",
            "error",
            "created_at",
            "updated_at",
        ]


class IngestionJobSerializer(serializers.ModelSerializer):
    targets = JobTargetSerializer(many=True, read_only=True)

    class Meta:
        model = IngestionJob
        fields = [
            "id",
            "status",
            "provider_preference",
            "tags",
            "notification_settings",
            "error",
            "cost_metadata",
            "result_metadata",
            "created_at",
            "updated_at",
            "completed_at",
            "targets",
        ]


class IngestRequestSerializer(serializers.Serializer):
    urls = serializers.ListField(
        child=serializers.URLField(max_length=2048),
        min_length=1,
        max_length=25,
    )
    provider_preference = serializers.ListField(
        child=serializers.ChoiceField(
            choices=["firecrawl", "zenrows", "bright_data", "tinyfish", "direct"]
        ),
        required=False,
        default=list,
    )
    tags = serializers.ListField(child=serializers.CharField(max_length=80), required=False, default=list)
    notify = serializers.BooleanField(required=False, default=True)
    telegram_chat_id = serializers.CharField(max_length=128, required=False, allow_blank=True)

    def validate_urls(self, urls: list[str]) -> list[str]:
        deduped = list(dict.fromkeys(urls))
        if len(deduped) != len(urls):
            return deduped
        return urls
