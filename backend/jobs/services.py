from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from ai.providers import GroqSummarizer
from integrations.fetchers import WebFetchService
from integrations.telegram import TelegramClient
from integrations.vector import VectorIndexService
from reports.models import SummaryReport
from sources.models import Document, Source

from .models import IngestionJob, JobTarget


class IngestionRunner:
    def __init__(self) -> None:
        self.fetcher = WebFetchService()
        self.summarizer = GroqSummarizer()
        self.vector_index = VectorIndexService()
        self.telegram = TelegramClient()

    def run(self, job_id: str) -> IngestionJob:
        job = IngestionJob.objects.prefetch_related("targets").get(id=job_id)
        job.status = IngestionJob.Status.RUNNING
        job.error = ""
        job.save(update_fields=["status", "error", "updated_at"])

        fetched_count = 0
        failed_count = 0
        providers_used: list[str] = []

        for target in job.targets.all():
            try:
                result = self.fetcher.fetch(target.url, job.provider_preference)
                with transaction.atomic():
                    source = Source.objects.create(
                        kind=Source.Kind.URL,
                        value=target.url,
                        tags=job.tags,
                        metadata={"provider": result.provider, **result.metadata},
                    )
                    document = Document.objects.create(
                        source=source,
                        url=result.url,
                        title=result.title,
                        content_markdown=result.content_markdown,
                        metadata=result.metadata,
                    )
                    ai_result = self.summarizer.summarize(result.content_markdown)
                    SummaryReport.objects.create(
                        job=job,
                        document=document,
                        prompt="default ingestion summary",
                        summary=ai_result.text,
                        model=ai_result.model,
                        metadata={"provider": ai_result.provider, **ai_result.metadata},
                    )
                    document.embedding_id = self.vector_index.upsert_document(document)
                    document.save(update_fields=["embedding_id"])
                    target.status = JobTarget.Status.FETCHED
                    target.fetched_with = result.provider
                    target.document = document
                    target.error = ""
                    target.save(update_fields=["status", "fetched_with", "document", "error", "updated_at"])
                providers_used.append(result.provider)
                fetched_count += 1
            except Exception as exc:
                failed_count += 1
                target.status = JobTarget.Status.FAILED
                target.error = str(exc)
                target.save(update_fields=["status", "error", "updated_at"])

        job.result_metadata = {
            "documents_created": fetched_count,
            "targets_failed": failed_count,
            "providers_used": sorted(set(providers_used)),
        }
        job.cost_metadata = {"mode": "mock" if fetched_count else "none", "estimated_usd": 0}
        job.completed_at = timezone.now()
        if fetched_count:
            job.status = IngestionJob.Status.COMPLETED
            job.error = ""
        else:
            job.status = IngestionJob.Status.FAILED
            job.error = "All targets failed."
        job.save(
            update_fields=[
                "status",
                "error",
                "result_metadata",
                "cost_metadata",
                "completed_at",
                "updated_at",
            ]
        )

        if job.notification_settings.get("notify", True):
            chat_id = job.notification_settings.get("telegram_chat_id")
            self.telegram.send_message(
                f"ToRsy job {job.id} finished: {job.status}, documents={fetched_count}, failed={failed_count}",
                chat_id=chat_id,
            )
        return job
