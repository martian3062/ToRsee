from django.db import models


class Source(models.Model):
    class Kind(models.TextChoices):
        URL = "url", "URL"
        SEARCH = "search", "Search"
        MANUAL = "manual", "Manual"

    kind = models.CharField(max_length=24, choices=Kind.choices, default=Kind.URL)
    value = models.TextField()
    tags = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.kind}:{self.value[:80]}"


class Document(models.Model):
    source = models.ForeignKey(Source, on_delete=models.SET_NULL, null=True, blank=True)
    url = models.URLField(max_length=2048, blank=True)
    title = models.CharField(max_length=512, blank=True)
    content_markdown = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    embedding_id = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["embedding_id"]),
        ]

    def __str__(self) -> str:
        return self.title or self.url or f"Document {self.pk}"
