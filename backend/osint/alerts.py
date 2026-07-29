from __future__ import annotations

import hashlib
import json
from datetime import timedelta
from typing import Any

from django.db import models
from django.utils import timezone

from integrations.telegram import TelegramClient

from .models import AlertEvent, AlertRule, MonitoredTarget


def _lookup(payload: dict[str, Any], key: str) -> Any:
    value: Any = payload
    for part in key.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def _equal(actual: Any, expected: Any) -> bool:
    if isinstance(expected, list):
        return any(_equal(actual, item) for item in expected)
    if isinstance(actual, str) and isinstance(expected, str):
        return actual.casefold() == expected.casefold()
    return actual == expected


def rule_matches(rule: AlertRule, payload: dict[str, Any]) -> bool:
    """Evaluate simple exact, minimum, maximum, and keyword conditions.

    Examples:
      {"as_number": "AS3320", "anomaly_type": "relay_offline"}
      {"country_code": "IR", "min_failure_rate": 0.3}
      {"keyword": "leak", "min_count": 2}
    """

    for key, expected in rule.conditions.items():
        if key == "keyword":
            hits = payload.get("keyword_hits") or {}
            if not any(
                str(keyword).casefold() == str(expected).casefold() and int(count) > 0
                for keyword, count in hits.items()
            ):
                return False
            continue
        if key == "min_count":
            hits = payload.get("keyword_hits") or {}
            if max((int(value) for value in hits.values()), default=0) < int(expected):
                return False
            continue
        if key.startswith("min_"):
            actual = _lookup(payload, key.removeprefix("min_"))
            try:
                if float(actual) < float(expected):
                    return False
            except (TypeError, ValueError):
                return False
            continue
        if key.startswith("max_"):
            actual = _lookup(payload, key.removeprefix("max_"))
            try:
                if float(actual) > float(expected):
                    return False
            except (TypeError, ValueError):
                return False
            continue
        if key.endswith("_contains"):
            actual = _lookup(payload, key.removesuffix("_contains"))
            if str(expected).casefold() not in str(actual or "").casefold():
                return False
            continue
        if not _equal(_lookup(payload, key), expected):
            return False
    return True


def _is_in_cooldown(rule: AlertRule) -> bool:
    if not rule.cooldown_minutes or not rule.last_triggered:
        return False
    return rule.last_triggered > timezone.now() - timedelta(minutes=rule.cooldown_minutes)


def _deliver(
    *,
    event_type: str,
    title: str,
    message: str,
    payload: dict[str, Any],
    severity: str,
    source_key: str,
    monitored_target: MonitoredTarget | None,
    rule: AlertRule | None,
) -> AlertEvent:
    identity = {
        "event_type": event_type,
        "source": source_key,
        "rule": rule.pk if rule else "system",
    }
    dedupe_key = hashlib.sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    event, created = AlertEvent.objects.get_or_create(
        dedupe_key=dedupe_key,
        defaults={
            "rule": rule,
            "monitored_target": monitored_target,
            "event_type": event_type,
            "severity": severity,
            "title": title,
            "message": message,
            "payload": payload,
        },
    )
    if not created:
        return event

    response = TelegramClient().send_message(f"[{severity.upper()}] {title}\n{message}")
    event.delivered = bool(response.get("ok"))
    event.delivery_response = response
    event.save(update_fields=["delivered", "delivery_response"])

    if rule:
        rule.last_triggered = timezone.now()
        rule.save(update_fields=["last_triggered", "updated_at"])
    return event


def emit_alert(
    *,
    event_type: str,
    title: str,
    message: str,
    payload: dict[str, Any],
    severity: str,
    source_key: str,
    monitored_target: MonitoredTarget | None = None,
    monitored_target_id: int | None = None,
    force: bool = False,
) -> list[AlertEvent]:
    """Fan an event out through matching rules, or through the built-in critical path."""

    if monitored_target is None and monitored_target_id is not None:
        monitored_target = MonitoredTarget.objects.filter(pk=monitored_target_id).first()

    candidates = AlertRule.objects.filter(event_type=event_type, enabled=True)
    if monitored_target:
        candidates = candidates.filter(
            models.Q(monitored_target__isnull=True) | models.Q(monitored_target=monitored_target)
        )
    else:
        candidates = candidates.filter(monitored_target__isnull=True)

    matching = [
        rule for rule in candidates if not _is_in_cooldown(rule) and rule_matches(rule, payload)
    ]
    if not matching and not force:
        return []

    rules: list[AlertRule | None] = matching or [None]
    return [
        _deliver(
            event_type=event_type,
            title=title,
            message=message,
            payload=payload,
            severity=severity,
            source_key=source_key,
            monitored_target=monitored_target,
            rule=rule,
        )
        for rule in rules
    ]
