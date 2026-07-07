from django.db import models


class SummaryReport(models.Model):
    job = models.ForeignKey("jobs.IngestionJob", related_name="reports", on_delete=models.CASCADE)
    document = models.ForeignKey(
        "sources.Document",
        related_name="reports",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    prompt = models.TextField(blank=True)
    summary = models.TextField()
    model = models.CharField(max_length=128, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Summary {self.pk} for {self.document_id or self.job_id}"
