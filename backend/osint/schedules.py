from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.db import transaction
from django.utils import timezone

from config.celery import app

from .models import DarkWebCrawl, MonitoredTarget, OSINTScan
from .tasks import run_darkweb_crawl_task, run_osint_scan_task


def _keywords(config: dict[str, Any]) -> str:
    value = config.get("keywords", "")
    if isinstance(value, list):
        return ",".join(str(item).strip() for item in value if str(item).strip())
    return str(value)


def dispatch_monitored_target(
    target: MonitoredTarget,
    *,
    mark_run: bool = True,
) -> dict[str, Any]:
    """Create the correct work record and hand it to Celery."""

    if not target.enabled:
        return {"target_id": target.id, "dispatched": False, "reason": "disabled"}

    if mark_run:
        target.last_run = timezone.now()
        target.save(update_fields=["last_run", "updated_at"])

    if target.kind == MonitoredTarget.Kind.ONION:
        record = DarkWebCrawl.objects.create(
            url=target.value,
            keywords=_keywords(target.config),
            monitored_target=target,
            status=DarkWebCrawl.Status.QUEUED,
        )
        result = run_darkweb_crawl_task.delay(record.id)
        return {
            "target_id": target.id,
            "dispatched": True,
            "record_type": "crawl",
            "record_id": record.id,
            "task_id": result.id,
        }

    scan_type = {
        MonitoredTarget.Kind.USERNAME: OSINTScan.ScanType.USERNAME,
        MonitoredTarget.Kind.DOMAIN: OSINTScan.ScanType.DOMAIN,
        MonitoredTarget.Kind.OONI: OSINTScan.ScanType.DOMAIN,
        MonitoredTarget.Kind.TOR_RELAY: OSINTScan.ScanType.TOR_RELAY,
    }.get(target.kind)
    if scan_type is None:
        return {"target_id": target.id, "dispatched": False, "reason": "unsupported kind"}

    scan = OSINTScan.objects.create(
        target=target.value,
        scan_type=scan_type,
        monitored_target=target,
        status=OSINTScan.Status.QUEUED,
    )
    result = run_osint_scan_task.delay(scan.id)
    return {
        "target_id": target.id,
        "dispatched": True,
        "record_type": "scan",
        "record_id": scan.id,
        "task_id": result.id,
    }


def _is_due(target: MonitoredTarget, now) -> bool:
    if not target.enabled:
        return False
    if target.last_run is None:
        return True
    return target.last_run <= now - timedelta(seconds=target.interval)


@app.task(name="osint.dispatch_due_monitored_targets")
def dispatch_due_monitored_targets() -> dict[str, Any]:
    """Beat entrypoint: claim and dispatch every target whose cadence elapsed."""

    now = timezone.now()
    dispatched: list[dict[str, Any]] = []
    target_ids = list(
        MonitoredTarget.objects.filter(enabled=True).values_list("id", flat=True)
    )
    for target_id in target_ids:
        with transaction.atomic():
            target = MonitoredTarget.objects.select_for_update().get(pk=target_id)
            if not _is_due(target, now):
                continue
            target.last_run = now
            target.save(update_fields=["last_run", "updated_at"])
        dispatched.append(dispatch_monitored_target(target, mark_run=False))
    return {"checked": len(target_ids), "dispatched": len(dispatched), "targets": dispatched}
