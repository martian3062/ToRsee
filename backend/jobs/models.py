import uuid

from django.db import models


class IngestionJob(models.Model):
    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.QUEUED)
    provider_preference = models.JSONField(default=list, blank=True)
    tags = models.JSONField(default=list, blank=True)
    notification_settings = models.JSONField(default=dict, blank=True)
    error = models.TextField(blank=True)
    cost_metadata = models.JSONField(default=dict, blank=True)
    result_metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.id} ({self.status})"


class JobTarget(models.Model):
    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        FETCHED = "fetched", "Fetched"
        FAILED = "failed", "Failed"

    job = models.ForeignKey(IngestionJob, related_name="targets", on_delete=models.CASCADE)
    url = models.URLField(max_length=2048)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.QUEUED)
    fetched_with = models.CharField(max_length=64, blank=True)
    document = models.ForeignKey(
        "sources.Document",
        related_name="job_targets",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.url} ({self.status})"
