from rest_framework import serializers

from .models import (
    CensorshipIncident,
    DarkWebCrawl,
    OSINTScan,
    RelayAnomaly,
)


class OSINTScanSerializer(serializers.ModelSerializer):
    class Meta:
        model = OSINTScan
        fields = [
            "id",
            "target",
            "scan_type",
            "status",
            "error",
            "results",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "status", "error", "results", "created_at", "updated_at"]


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
            "status",
            "routed_via_tor",
            "is_onion",
            "error",
            "results",
            "created_at",
            "updated_at",
        ]
