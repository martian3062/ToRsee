from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from .models import (
    AlertEvent,
    AlertRule,
    CensorshipIncident,
    DarkWebCrawl,
    MonitoredTarget,
    OSINTScan,
    RelayAnomaly,
    Snapshot,
)


class OSINTScanSerializer(serializers.ModelSerializer):
    class Meta:
        model = OSINTScan
        fields = [
            "id",
            "target",
            "scan_type",
            "monitored_target",
            "status",
            "error",
            "results",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "monitored_target",
            "status",
            "error",
            "results",
            "created_at",
            "updated_at",
        ]


class CensorshipIncidentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CensorshipIncident
        fields = [
            "id",
            "country_code",
            "asn",
            "target_domain",
            "anomaly_type",
            "measurement_count",
            "failure_rate",
            "reported_at",
        ]


class RelayAnomalySerializer(serializers.ModelSerializer):
    class Meta:
        model = RelayAnomaly
        fields = [
            "id",
            "fingerprint",
            "nickname",
            "country_code",
            "country_name",
            "as_number",
            "latitude",
            "longitude",
            "metric",
            "anomaly_type",
            "score",
            "severity",
            "detector",
            "detail",
            "detected_at",
        ]


class DarkWebCrawlSerializer(serializers.ModelSerializer):
    class Meta:
        model = DarkWebCrawl
        fields = [
            "id",
            "url",
            "keywords",
            "monitored_target",
            "status",
            "routed_via_tor",
            "is_onion",
            "error",
            "results",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "monitored_target",
            "status",
            "routed_via_tor",
            "is_onion",
            "error",
            "results",
            "created_at",
            "updated_at",
        ]


class MonitoredTargetSerializer(serializers.ModelSerializer):
    next_run = serializers.SerializerMethodField()

    class Meta:
        model = MonitoredTarget
        fields = [
            "id",
            "kind",
            "value",
            "interval",
            "enabled",
            "config",
            "last_run",
            "next_run",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "last_run", "next_run", "created_at", "updated_at"]

    def validate_interval(self, value):
        if value < 60:
            raise serializers.ValidationError("Monitoring intervals must be at least 60 seconds.")
        return value

    def validate_config(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Config must be a JSON object.")
        return value

    def get_next_run(self, obj):
        if not obj.enabled:
            return None
        if obj.last_run is None:
            return timezone.now()
        return obj.last_run + timedelta(seconds=obj.interval)


class SnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = Snapshot
        fields = [
            "id",
            "source_type",
            "target",
            "content_hash",
            "changed",
            "diff",
            "monitored_target",
            "osint_scan",
            "darkweb_crawl",
            "previous",
            "created_at",
        ]


class AlertRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AlertRule
        fields = [
            "id",
            "name",
            "event_type",
            "conditions",
            "enabled",
            "monitored_target",
            "cooldown_minutes",
            "last_triggered",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "last_triggered", "created_at", "updated_at"]

    def validate_conditions(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Conditions must be a JSON object.")
        return value


class AlertEventSerializer(serializers.ModelSerializer):
    rule_name = serializers.CharField(source="rule.name", read_only=True, default="")

    class Meta:
        model = AlertEvent
        fields = [
            "id",
            "rule",
            "rule_name",
            "monitored_target",
            "event_type",
            "severity",
            "title",
            "message",
            "payload",
            "delivered",
            "created_at",
        ]
