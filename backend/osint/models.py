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
    monitored_target = models.ForeignKey(
        "MonitoredTarget",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="scans",
    )
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
    monitored_target = models.ForeignKey(
        "MonitoredTarget",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="crawls",
    )
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


class MonitoredTarget(models.Model):
    """A target that Celery Beat re-checks on a user-defined cadence."""

    class Kind(models.TextChoices):
        USERNAME = "username", "Username"
        DOMAIN = "domain", "Domain"
        OONI = "ooni", "OONI domain"
        TOR_RELAY = "tor_relay", "Tor relay"
        ONION = "onion", "Onion URL"

    kind = models.CharField(max_length=24, choices=Kind.choices)
    value = models.CharField(max_length=1024)
    interval = models.PositiveIntegerField(
        default=3600,
        help_text="Seconds between scheduled checks.",
    )
    enabled = models.BooleanField(default=True)
    config = models.JSONField(default=dict, blank=True)
    last_run = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["kind", "value"]
        constraints = [
            models.UniqueConstraint(
                fields=["kind", "value"],
                name="unique_monitored_target",
            )
        ]
        indexes = [models.Index(fields=["enabled", "last_run"])]

    def __str__(self) -> str:
        return f"{self.kind}: {self.value}"


class Snapshot(models.Model):
    """A stable, hashable result used to detect meaningful monitoring changes."""

    class SourceType(models.TextChoices):
        USERNAME = "username", "Username scan"
        CRAWL = "crawl", "Web crawl"

    source_type = models.CharField(max_length=24, choices=SourceType.choices)
    target = models.CharField(max_length=1024)
    content_hash = models.CharField(max_length=64)
    payload = models.JSONField(default=dict)
    changed = models.BooleanField(default=False)
    diff = models.JSONField(default=dict, blank=True)
    monitored_target = models.ForeignKey(
        MonitoredTarget,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="snapshots",
    )
    osint_scan = models.ForeignKey(
        OSINTScan,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="snapshots",
    )
    darkweb_crawl = models.ForeignKey(
        DarkWebCrawl,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="snapshots",
    )
    previous = models.ForeignKey(
        "self",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="next_snapshots",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["source_type", "target", "created_at"])]

    def __str__(self) -> str:
        state = "changed" if self.changed else "baseline"
        return f"{self.source_type}: {self.target} ({state})"


class AlertRule(models.Model):
    """User-defined filters for turning monitoring events into notifications."""

    class EventType(models.TextChoices):
        RELAY_ANOMALY = "relay_anomaly", "Relay anomaly"
        CENSORSHIP = "censorship", "Censorship incident"
        KEYWORD_HIT = "keyword_hit", "Crawler keyword hit"
        CHANGE = "change", "Snapshot change"
        DRUG_SIGNAL = "drug_signal", "Drug-intelligence signal"

    name = models.CharField(max_length=128)
    event_type = models.CharField(max_length=24, choices=EventType.choices)
    conditions = models.JSONField(default=dict, blank=True)
    enabled = models.BooleanField(default=True)
    monitored_target = models.ForeignKey(
        MonitoredTarget,
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="alert_rules",
    )
    cooldown_minutes = models.PositiveIntegerField(default=0)
    last_triggered = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class AlertEvent(models.Model):
    """An auditable Telegram fan-out attempt for a built-in or custom rule."""

    class Severity(models.TextChoices):
        INFO = "info", "Info"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"

    rule = models.ForeignKey(
        AlertRule,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="events",
    )
    monitored_target = models.ForeignKey(
        MonitoredTarget,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="alert_events",
    )
    event_type = models.CharField(max_length=24, choices=AlertRule.EventType.choices)
    severity = models.CharField(max_length=8, choices=Severity.choices, default=Severity.INFO)
    title = models.CharField(max_length=256)
    message = models.TextField()
    payload = models.JSONField(default=dict, blank=True)
    dedupe_key = models.CharField(max_length=64, unique=True)
    delivered = models.BooleanField(default=False)
    delivery_response = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["event_type", "created_at"]),
            models.Index(fields=["delivered", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.event_type}: {self.title}"
