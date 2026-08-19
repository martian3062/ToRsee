from __future__ import annotations

from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from .models import IntelligenceSource
from .services import ingest_telegram_update


def _mock_update(source: IntelligenceSource) -> dict:
    message_id = int(source.latest_cursor or "0") + 1
    return {
        "update_id": 8_000_000 + source.id * 1_000 + message_id,
        "channel_post": {
            "message_id": message_id,
            "date": int(timezone.now().timestamp()),
            "chat": {"id": int(source.external_id), "title": source.display_name},
            "from": {"id": 1, "username": "approved_source"},
            "text": (
                "Mock approved-source message: fentanyl available for sale. "
                "Delivery is mentioned; contact @samplevendor."
            ),
        },
    }


@shared_task(name="drugintel.ingest_telegram_update")
def ingest_telegram_update_task(update: dict) -> dict:
    return ingest_telegram_update(update)


@shared_task(name="drugintel.run_intelligence_source")
def run_intelligence_source(source_id: int) -> dict:
    source = IntelligenceSource.objects.filter(pk=source_id).first()
    if not source:
        return {"outcome": "missing_source", "source_id": source_id}
    if not source.enabled or source.authorization_status != IntelligenceSource.AuthorizationStatus.APPROVED:
        return {"outcome": "blocked", "reason": "source_not_approved", "source_id": source_id}
    if source.platform != IntelligenceSource.Platform.TELEGRAM:
        return {"outcome": "blocked", "reason": "unsupported_platform", "source_id": source_id}
    if settings.PROVIDER_MOCK_MODE:
        return ingest_telegram_update(_mock_update(source))
    if not settings.INTELLIGENCE_LIVE_ENABLED:
        return {"outcome": "blocked", "reason": "live_collection_disabled", "source_id": source_id}
    source.last_collected_at = timezone.now()
    source.save(update_fields=["last_collected_at", "updated_at"])
    return {
        "outcome": "webhook_only",
        "source_id": source_id,
        "detail": "Live Telegram Bot collection is event-driven and only accepts signed updates.",
    }


@shared_task(name="drugintel.dispatch_due_sources")
def dispatch_due_sources() -> dict:
    now = timezone.now()
    due = IntelligenceSource.objects.filter(
        enabled=True,
        authorization_status=IntelligenceSource.AuthorizationStatus.APPROVED,
    )
    dispatched: list[int] = []
    for source in due:
        if source.last_collected_at and source.last_collected_at > now - timedelta(seconds=source.interval):
            continue
        run_intelligence_source.delay(source.id)
        dispatched.append(source.id)
    return {"checked": due.count(), "dispatched": dispatched}
