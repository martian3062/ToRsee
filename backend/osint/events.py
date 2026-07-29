import asyncio
import json
import time
from collections.abc import AsyncIterator
from collections.abc import Iterator

from asgiref.sync import sync_to_async
from django.http import StreamingHttpResponse
from django.utils import timezone
from django.views import View

from .models import AlertEvent, AlertRule, MonitoredTarget, Snapshot


def monitoring_state() -> dict:
    """Return a small cursor payload suitable for cache invalidation."""

    latest_snapshot = Snapshot.objects.order_by("-id").values_list("id", flat=True).first()
    latest_event = AlertEvent.objects.order_by("-id").values_list("id", flat=True).first()
    return {
        "targets": MonitoredTarget.objects.count(),
        "enabled_targets": MonitoredTarget.objects.filter(enabled=True).count(),
        "snapshots": Snapshot.objects.count(),
        "latest_snapshot_id": latest_snapshot,
        "rules": AlertRule.objects.count(),
        "events": AlertEvent.objects.count(),
        "latest_event_id": latest_event,
    }


def encode_event(payload: dict, event: str = "monitoring") -> bytes:
    body = json.dumps(payload, separators=(",", ":"))
    return f"event: {event}\ndata: {body}\n\n".encode()


def event_payload(state: dict) -> dict:
    return {
        **state,
        "observed_at": timezone.now().isoformat(),
    }


def monitoring_event_stream_sync(once: bool = False) -> Iterator[bytes]:
    """Serve the development WSGI server without buffering an async iterator."""

    previous: dict | None = None
    heartbeat = 0

    while True:
        state = monitoring_state()
        if state != previous:
            yield encode_event(event_payload(state))
            previous = state

        if once:
            return

        heartbeat += 1
        if heartbeat % 10 == 0:
            yield b": keep-alive\n\n"
        time.sleep(2)


async def monitoring_event_stream(once: bool = False) -> AsyncIterator[bytes]:
    previous: dict | None = None
    heartbeat = 0

    while True:
        state = await sync_to_async(monitoring_state, thread_sensitive=True)()
        if state != previous:
            yield encode_event(event_payload(state))
            previous = state

        if once:
            return

        heartbeat += 1
        if heartbeat % 10 == 0:
            yield b": keep-alive\n\n"
        await asyncio.sleep(2)


class MonitoringEventStreamView(View):
    """One-way live updates for the monitoring dashboard."""

    def get(self, request):
        once = request.GET.get("once") == "1"
        stream = (
            monitoring_event_stream(once=once)
            if hasattr(request, "scope")
            else monitoring_event_stream_sync(once=once)
        )
        response = StreamingHttpResponse(
            stream,
            content_type="text/event-stream",
        )
        response["Cache-Control"] = "no-cache, no-transform"
        response["X-Accel-Buffering"] = "no"
        return response
