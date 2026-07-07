from django.db import models


class OSINTScan(models.Model):
    class ScanType(models.TextChoices):
        USERNAME = "username", "Username Search"
        DOMAIN = "domain", "Domain Attack Surface"
        METADATA = "metadata", "Document OpSec Analyzer"
        TOR_RELAY = "tor_relay", "Tor Network Anomaly"

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    target = models.CharField(max_length=512)
    scan_type = models.CharField(max_length=24, choices=ScanType.choices)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.QUEUED)
    error = models.TextField(blank=True)
    results = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["scan_type"]),
        ]

    def __str__(self) -> str:
        return f"{self.scan_type} scan of {self.target} ({self.status})"


class CensorshipIncident(models.Model):
    country_code = models.CharField(max_length=8)  # e.g., "US", "IR", "RU"
    asn = models.CharField(max_length=32)           # e.g., "AS1234"
    target_domain = models.CharField(max_length=512)
    anomaly_type = models.CharField(max_length=128)  # DNS, TCP, HTTP blocking
    measurement_count = models.IntegerField(default=1)
    failure_rate = models.FloatField(default=0.0)
    reported_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-reported_at"]

    def __str__(self) -> str:
        return f"{self.country_code} ({self.asn}) - {self.target_domain} ({self.anomaly_type})"


class RelayObservation(models.Model):
    """A single point-in-time metric sample for a Tor relay (time-series row).

    Populated from Onionoo /bandwidth + /uptime history so the anomaly engine
    has a per-relay baseline to score against instead of a lone snapshot.
    """

    fingerprint = models.CharField(max_length=64, db_index=True)
    nickname = models.CharField(max_length=64, blank=True)
    country_code = models.CharField(max_length=8, blank=True)
    country_name = models.CharField(max_length=64, blank=True)
    as_number = models.CharField(max_length=32, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    observed_bandwidth = models.BigIntegerField(default=0)
    consensus_weight = models.BigIntegerField(default=0)
    running = models.BooleanField(default=True)
    observed_at = models.DateTimeField()

    class Meta:
        ordering = ["fingerprint", "observed_at"]
        indexes = [
            models.Index(fields=["fingerprint", "observed_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.nickname or self.fingerprint[:8]} @ {self.observed_at:%Y-%m-%d %H:%M}"


class RelayAnomaly(models.Model):
    """An anomaly flagged by the PyOD time-series engine for one relay."""

    class Severity(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"

    fingerprint = models.CharField(max_length=64, db_index=True)
    nickname = models.CharField(max_length=64, blank=True)
    country_code = models.CharField(max_length=8, blank=True)
    country_name = models.CharField(max_length=64, blank=True)
    as_number = models.CharField(max_length=32, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    metric = models.CharField(max_length=32, default="observed_bandwidth")
    anomaly_type = models.CharField(max_length=64, default="bandwidth_spike")
    score = models.FloatField(default=0.0)  # 0..1 normalized anomaly score
    severity = models.CharField(max_length=8, choices=Severity.choices, default=Severity.LOW)
    detector = models.CharField(max_length=32, default="TimeSeriesOD")
    detail = models.JSONField(default=dict, blank=True)
    detected_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-score", "-detected_at"]
        indexes = [models.Index(fields=["severity"])]

    def __str__(self) -> str:
        return f"{self.anomaly_type} {self.nickname or self.fingerprint[:8]} ({self.severity})"


class DarkWebCrawl(models.Model):
    """A crawl of a clearnet or .onion URL routed through the Tor SOCKS proxy."""

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    url = models.CharField(max_length=1024)
    keywords = models.CharField(max_length=512, blank=True)  # comma separated watch terms
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.QUEUED)
    routed_via_tor = models.BooleanField(default=False)
    is_onion = models.BooleanField(default=False)
    error = models.TextField(blank=True)
    results = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"crawl {self.url} ({self.status})"
