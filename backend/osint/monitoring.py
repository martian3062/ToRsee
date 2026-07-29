from __future__ import annotations

import hashlib
import json
from typing import Any

from .alerts import emit_alert
from .models import AlertEvent, AlertRule, DarkWebCrawl, MonitoredTarget, OSINTScan, Snapshot


def _stable_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _diff(previous: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    previous_keys = set(previous)
    current_keys = set(current)
    changed_fields = sorted(
        key for key in previous_keys & current_keys if previous.get(key) != current.get(key)
    )
    result: dict[str, Any] = {
        "added_fields": sorted(current_keys - previous_keys),
        "removed_fields": sorted(previous_keys - current_keys),
        "changed_fields": changed_fields,
    }

    old_accounts = {
        item.get("url")
        for item in previous.get("found_accounts", [])
        if isinstance(item, dict) and item.get("url")
    }
    new_accounts = {
        item.get("url")
        for item in current.get("found_accounts", [])
        if isinstance(item, dict) and item.get("url")
    }
    if old_accounts or new_accounts:
        result["accounts_added"] = sorted(new_accounts - old_accounts)
        result["accounts_removed"] = sorted(old_accounts - new_accounts)

    old_hits = previous.get("keyword_hits") or {}
    new_hits = current.get("keyword_hits") or {}
    if old_hits or new_hits:
        result["keyword_delta"] = {
            keyword: int(new_hits.get(keyword, 0)) - int(old_hits.get(keyword, 0))
            for keyword in sorted(set(old_hits) | set(new_hits))
            if int(new_hits.get(keyword, 0)) != int(old_hits.get(keyword, 0))
        }
    return result


def record_snapshot(
    *,
    source_type: str,
    target: str,
    payload: dict[str, Any],
    monitored_target: MonitoredTarget | None = None,
    osint_scan: OSINTScan | None = None,
    darkweb_crawl: DarkWebCrawl | None = None,
) -> Snapshot:
    previous = (
        Snapshot.objects.filter(source_type=source_type, target=target)
        .order_by("-created_at")
        .first()
    )
    content_hash = _stable_hash(payload)
    changed = bool(previous and previous.content_hash != content_hash)
    diff = _diff(previous.payload, payload) if changed and previous else {}
    snapshot = Snapshot.objects.create(
        source_type=source_type,
        target=target,
        content_hash=content_hash,
        payload=payload,
        changed=changed,
        diff=diff,
        monitored_target=monitored_target,
        osint_scan=osint_scan,
        darkweb_crawl=darkweb_crawl,
        previous=previous,
    )

    if changed:
        summary_parts = []
        for key in ("accounts_added", "accounts_removed", "keyword_delta", "changed_fields"):
            value = diff.get(key)
            if value:
                summary_parts.append(f"{key.replace('_', ' ')}: {value}")
        summary = "; ".join(summary_parts) or "The monitored result changed."
        emit_alert(
            event_type=AlertRule.EventType.CHANGE,
            title=f"Change detected for {target}",
            message=summary,
            payload={
                "source_type": source_type,
                "target": target,
                "diff": diff,
                "snapshot_id": snapshot.id,
            },
            severity=AlertEvent.Severity.MEDIUM,
            source_key=f"snapshot:{snapshot.id}",
            monitored_target=monitored_target,
            force=True,
        )
    return snapshot
