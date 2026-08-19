from django.db import models


class Investigation(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        PAUSED = "paused", "Paused"
        CLOSED = "closed", "Closed"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"

    name = models.CharField(max_length=256)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN)
    priority = models.CharField(max_length=16, choices=Priority.choices, default=Priority.MEDIUM)
    authorization_reference = models.CharField(max_length=256, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "name"]

    def __str__(self) -> str:
        return self.name


class IntelligenceSource(models.Model):
    class Platform(models.TextChoices):
        TELEGRAM = "telegram", "Telegram"
        ONION = "onion", "Onion service"
        MANUAL = "manual", "Manual evidence"

    class CollectionMode(models.TextChoices):
        BOT_WEBHOOK = "bot_webhook", "Telegram Bot webhook"
        APPROVED_PUBLIC = "approved_public", "Approved public source"
        MANUAL = "manual", "Manual import"

    class AuthorizationStatus(models.TextChoices):
        PENDING = "pending", "Pending approval"
        APPROVED = "approved", "Approved"
        SUSPENDED = "suspended", "Suspended"

    investigation = models.ForeignKey(
        Investigation,
        related_name="sources",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    platform = models.CharField(max_length=24, choices=Platform.choices, default=Platform.TELEGRAM)
    external_id = models.CharField(max_length=128)
    display_name = models.CharField(max_length=256)
    public_url = models.URLField(max_length=1024, blank=True)
    collection_mode = models.CharField(
        max_length=32,
        choices=CollectionMode.choices,
        default=CollectionMode.BOT_WEBHOOK,
    )
    authorization_status = models.CharField(
        max_length=16,
        choices=AuthorizationStatus.choices,
        default=AuthorizationStatus.PENDING,
    )
    enabled = models.BooleanField(default=False)
    interval = models.PositiveIntegerField(default=3600)
    latest_cursor = models.CharField(max_length=128, blank=True)
    last_collected_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["platform", "display_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["platform", "external_id"],
                name="unique_intel_source_platform_external_id",
            )
        ]
        indexes = [models.Index(fields=["enabled", "authorization_status", "last_collected_at"])]

    def __str__(self) -> str:
        return f"{self.platform}: {self.display_name}"


class TelegramUpdateReceipt(models.Model):
    update_id = models.BigIntegerField(unique=True)
    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    outcome = models.CharField(max_length=32, default="received")
    detail = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-received_at"]


class EvidenceItem(models.Model):
    class Kind(models.TextChoices):
        TELEGRAM_MESSAGE = "telegram_message", "Telegram message"
        ONION_CRAWL = "onion_crawl", "Onion crawl"
        MANUAL = "manual", "Manual evidence"

    source = models.ForeignKey(IntelligenceSource, related_name="evidence", on_delete=models.CASCADE)
    investigation = models.ForeignKey(
        Investigation,
        related_name="evidence",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    kind = models.CharField(max_length=32, choices=Kind.choices, default=Kind.TELEGRAM_MESSAGE)
    external_id = models.CharField(max_length=128)
    version = models.PositiveIntegerField(default=1)
    is_latest = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    author_alias = models.CharField(max_length=256, blank=True)
    reply_to_external_id = models.CharField(max_length=128, blank=True)
    forwarded_from = models.CharField(max_length=256, blank=True)
    public_url = models.URLField(max_length=1024, blank=True)
    content = models.TextField(blank=True)
    normalized_content = models.TextField(blank=True)
    content_hash = models.CharField(max_length=64)
    raw_payload = models.JSONField(default=dict, blank=True)
    occurred_at = models.DateTimeField(null=True, blank=True)
    captured_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-occurred_at", "-captured_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["source", "external_id", "version"],
                name="unique_evidence_source_external_version",
            )
        ]
        indexes = [
            models.Index(fields=["source", "external_id", "is_latest"]),
            models.Index(fields=["investigation", "occurred_at"]),
            models.Index(fields=["content_hash"]),
        ]

    def __str__(self) -> str:
        return f"{self.kind} {self.source_id}:{self.external_id} v{self.version}"


class DrugSignal(models.Model):
    class SignalType(models.TextChoices):
        ILLICIT_SALE = "illicit_sale", "Potential illicit drug sale"
        CONTROLLED_SUBSTANCE = "controlled_substance", "Controlled substance reference"

    class ReviewStatus(models.TextChoices):
        NEW = "new", "New"
        TRIAGED = "triaged", "Triaged"
        CORROBORATED = "corroborated", "Corroborated"
        FALSE_POSITIVE = "false_positive", "False positive"
        ESCALATED = "escalated", "Escalated"
        CLOSED = "closed", "Closed"

    evidence = models.ForeignKey(EvidenceItem, related_name="signals", on_delete=models.CASCADE)
    investigation = models.ForeignKey(
        Investigation,
        related_name="signals",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    signal_type = models.CharField(max_length=32, choices=SignalType.choices)
    risk_score = models.PositiveSmallIntegerField(default=0)
    matched_terms = models.JSONField(default=list, blank=True)
    evidence_spans = models.JSONField(default=list, blank=True)
    rule_version = models.CharField(max_length=64, default="drug-intel-rules-v1")
    review_status = models.CharField(
        max_length=24,
        choices=ReviewStatus.choices,
        default=ReviewStatus.NEW,
    )
    reviewed_by = models.CharField(max_length=128, blank=True)
    review_note = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-risk_score", "-created_at"]
        indexes = [
            models.Index(fields=["review_status", "risk_score"]),
            models.Index(fields=["investigation", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.signal_type} ({self.risk_score})"


class Entity(models.Model):
    class Kind(models.TextChoices):
        TELEGRAM_CHANNEL = "telegram_channel", "Telegram channel"
        TELEGRAM_HANDLE = "telegram_handle", "Telegram handle"
        URL = "url", "URL"
        ONION = "onion", "Onion address"
        DOMAIN = "domain", "Domain"
        CONTACT = "contact", "Contact indicator"

    kind = models.CharField(max_length=32, choices=Kind.choices)
    value = models.CharField(max_length=1024)
    normalized_value = models.CharField(max_length=1024)
    display_name = models.CharField(max_length=1024, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["kind", "normalized_value"]
        constraints = [
            models.UniqueConstraint(
                fields=["kind", "normalized_value"],
                name="unique_entity_kind_normalized_value",
            )
        ]

    def __str__(self) -> str:
        return self.display_name or self.value


class EvidenceEntity(models.Model):
    evidence = models.ForeignKey(EvidenceItem, related_name="entity_links", on_delete=models.CASCADE)
    entity = models.ForeignKey(Entity, related_name="evidence_links", on_delete=models.CASCADE)
    role = models.CharField(max_length=64, default="mentioned")
    evidence_span = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["evidence", "entity", "role"],
                name="unique_evidence_entity_role",
            )
        ]


class EntityRelationship(models.Model):
    source_entity = models.ForeignKey(Entity, related_name="outgoing_relationships", on_delete=models.CASCADE)
    target_entity = models.ForeignKey(Entity, related_name="incoming_relationships", on_delete=models.CASCADE)
    relationship_type = models.CharField(max_length=64)
    evidence = models.ForeignKey(
        EvidenceItem,
        related_name="relationships",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    confidence = models.FloatField(default=1.0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["relationship_type", "created_at"])]


class CorrelationFinding(models.Model):
    class Severity(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"

    investigation = models.ForeignKey(
        Investigation,
        related_name="correlations",
        on_delete=models.CASCADE,
    )
    dedupe_key = models.CharField(max_length=128, unique=True)
    title = models.CharField(max_length=256)
    description = models.TextField()
    severity = models.CharField(max_length=16, choices=Severity.choices, default=Severity.MEDIUM)
    supporting_evidence_ids = models.JSONField(default=list, blank=True)
    entity_ids = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-severity"]


class ReviewDecision(models.Model):
    signal = models.ForeignKey(DrugSignal, related_name="decisions", on_delete=models.CASCADE)
    status = models.CharField(max_length=24, choices=DrugSignal.ReviewStatus.choices)
    reviewer = models.CharField(max_length=128)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
