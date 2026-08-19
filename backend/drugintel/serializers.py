from datetime import datetime, timedelta

from django.utils import timezone
from rest_framework import serializers

from .models import (
    CorrelationFinding,
    DrugSignal,
    Entity,
    EvidenceItem,
    IntelligenceSource,
    Investigation,
    ReviewDecision,
)


class InvestigationSerializer(serializers.ModelSerializer):
    source_count = serializers.IntegerField(read_only=True)
    signal_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Investigation
        fields = [
            "id", "name", "description", "status", "priority", "authorization_reference",
            "source_count", "signal_count", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "source_count", "signal_count", "created_at", "updated_at"]


class IntelligenceSourceSerializer(serializers.ModelSerializer):
    next_run = serializers.SerializerMethodField()
    evidence_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = IntelligenceSource
        fields = [
            "id", "investigation", "platform", "external_id", "display_name", "public_url",
            "collection_mode", "authorization_status", "enabled", "interval", "latest_cursor",
            "last_collected_at", "next_run", "evidence_count", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "latest_cursor", "last_collected_at", "next_run", "evidence_count",
            "created_at", "updated_at",
        ]

    def validate_interval(self, value):
        if value < 60:
            raise serializers.ValidationError("Collection intervals must be at least 60 seconds.")
        return value

    def validate(self, attrs):
        platform = attrs.get("platform", getattr(self.instance, "platform", None))
        mode = attrs.get("collection_mode", getattr(self.instance, "collection_mode", None))
        external_id = attrs.get("external_id", getattr(self.instance, "external_id", ""))
        if platform == IntelligenceSource.Platform.TELEGRAM and mode == IntelligenceSource.CollectionMode.MANUAL:
            raise serializers.ValidationError("Telegram sources must use Bot webhook or approved public mode.")
        if platform == IntelligenceSource.Platform.TELEGRAM and mode == IntelligenceSource.CollectionMode.BOT_WEBHOOK:
            try:
                int(external_id)
            except (TypeError, ValueError):
                raise serializers.ValidationError(
                    {"external_id": "Telegram Bot sources require the numeric chat ID from an approved source."}
                )
        return attrs

    def get_next_run(self, obj: IntelligenceSource) -> datetime | None:
        if not obj.enabled or obj.authorization_status != IntelligenceSource.AuthorizationStatus.APPROVED:
            return None
        if not obj.last_collected_at:
            return timezone.now()
        return obj.last_collected_at + timedelta(seconds=obj.interval)


class EvidenceItemSerializer(serializers.ModelSerializer):
    source_name = serializers.CharField(source="source.display_name", read_only=True)
    signal_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = EvidenceItem
        fields = [
            "id", "source", "source_name", "investigation", "kind", "external_id", "version",
            "is_latest", "is_deleted", "author_alias", "reply_to_external_id", "forwarded_from",
            "public_url", "content", "normalized_content", "content_hash", "occurred_at", "captured_at",
            "signal_count",
        ]
        read_only_fields = fields


class DrugSignalSerializer(serializers.ModelSerializer):
    source_name = serializers.CharField(source="evidence.source.display_name", read_only=True)
    evidence_external_id = serializers.CharField(source="evidence.external_id", read_only=True)

    class Meta:
        model = DrugSignal
        fields = [
            "id", "evidence", "evidence_external_id", "source_name", "investigation", "signal_type",
            "risk_score", "matched_terms", "evidence_spans", "rule_version", "review_status",
            "reviewed_by", "review_note", "reviewed_at", "created_at", "updated_at",
        ]
        read_only_fields = fields


class SignalReviewSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=DrugSignal.ReviewStatus.choices)
    reviewer = serializers.CharField(max_length=128)
    note = serializers.CharField(required=False, allow_blank=True, max_length=4000)

    def apply(self, signal: DrugSignal) -> DrugSignal:
        data = self.validated_data
        signal.review_status = data["status"]
        signal.reviewed_by = data["reviewer"]
        signal.review_note = data.get("note", "")
        signal.reviewed_at = timezone.now()
        signal.save(update_fields=["review_status", "reviewed_by", "review_note", "reviewed_at", "updated_at"])
        ReviewDecision.objects.create(
            signal=signal,
            status=signal.review_status,
            reviewer=signal.reviewed_by,
            note=signal.review_note,
        )
        return signal


class EntitySerializer(serializers.ModelSerializer):
    evidence_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Entity
        fields = [
            "id", "kind", "value", "normalized_value", "display_name", "evidence_count", "created_at", "updated_at",
        ]
        read_only_fields = fields


class CorrelationFindingSerializer(serializers.ModelSerializer):
    class Meta:
        model = CorrelationFinding
        fields = [
            "id", "investigation", "title", "description", "severity", "supporting_evidence_ids",
            "entity_ids", "created_at", "updated_at",
        ]
        read_only_fields = fields
