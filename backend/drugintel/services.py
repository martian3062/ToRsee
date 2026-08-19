from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone as datetime_timezone
from typing import Any

from django.db import transaction
from django.db.models import Count
from django.utils import timezone

from osint.alerts import emit_alert
from osint.models import AlertEvent, AlertRule

from .models import (
    CorrelationFinding,
    DrugSignal,
    Entity,
    EntityRelationship,
    EvidenceEntity,
    EvidenceItem,
    IntelligenceSource,
    TelegramUpdateReceipt,
)
from .rules import RULE_VERSION, evaluate_drug_signal, extract_indicators


def _content_hash(content: str, raw_payload: dict[str, Any]) -> str:
    payload = json.dumps(raw_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(f"{content}\n{payload}".encode("utf-8")).hexdigest()


def _occurred_at(value: Any):
    if not isinstance(value, (int, float)):
        return None
    return datetime.fromtimestamp(value, tz=datetime_timezone.utc)


def _message_from_update(update: dict[str, Any]) -> tuple[dict[str, Any] | None, bool]:
    for key in ("edited_channel_post", "edited_message", "channel_post", "message"):
        message = update.get(key)
        if isinstance(message, dict):
            return message, key.startswith("edited_")
    return None, False


def _source_for_message(message: dict[str, Any]) -> IntelligenceSource | None:
    chat = message.get("chat") or {}
    external_id = str(chat.get("id") or "")
    if not external_id:
        return None
    return (
        IntelligenceSource.objects.filter(
            platform=IntelligenceSource.Platform.TELEGRAM,
            external_id=external_id,
            collection_mode=IntelligenceSource.CollectionMode.BOT_WEBHOOK,
            authorization_status=IntelligenceSource.AuthorizationStatus.APPROVED,
            enabled=True,
        )
        .select_related("investigation")
        .first()
    )


def _entity(kind: str, value: str) -> Entity:
    normalized = value.casefold().strip()
    return Entity.objects.get_or_create(
        kind=kind,
        normalized_value=normalized,
        defaults={"value": value, "display_name": value},
    )[0]


def _link_evidence_entities(evidence: EvidenceItem) -> list[Entity]:
    entities: list[Entity] = []
    if evidence.source.platform == IntelligenceSource.Platform.TELEGRAM:
        source_entity, _ = Entity.objects.get_or_create(
            kind=Entity.Kind.TELEGRAM_CHANNEL,
            normalized_value=f"telegram:{evidence.source.external_id}",
            defaults={
                "value": f"telegram:{evidence.source.external_id}",
                "display_name": evidence.source.display_name,
            },
        )
    else:
        source_entity = _entity(Entity.Kind.ONION, evidence.source.external_id)
    EvidenceEntity.objects.get_or_create(evidence=evidence, entity=source_entity, role="published_in")
    entities.append(source_entity)

    if evidence.author_alias:
        author = _entity(Entity.Kind.TELEGRAM_HANDLE, evidence.author_alias)
        EvidenceEntity.objects.get_or_create(evidence=evidence, entity=author, role="authored_by")
        EntityRelationship.objects.get_or_create(
            source_entity=author,
            target_entity=source_entity,
            relationship_type="published_in",
            evidence=evidence,
        )
        entities.append(author)

    for indicator in extract_indicators(evidence.normalized_content):
        item = _entity(indicator["kind"], indicator["value"])
        EvidenceEntity.objects.get_or_create(evidence=evidence, entity=item, role="mentioned")
        EntityRelationship.objects.get_or_create(
            source_entity=source_entity,
            target_entity=item,
            relationship_type="mentions",
            evidence=evidence,
        )
        entities.append(item)
    return entities


def ingest_onion_crawl(crawl) -> dict[str, Any]:
    """Promote an approved dark-web crawl into the shared evidence ledger."""

    source = (
        IntelligenceSource.objects.filter(
            platform=IntelligenceSource.Platform.ONION,
            external_id=crawl.url,
            authorization_status=IntelligenceSource.AuthorizationStatus.APPROVED,
            enabled=True,
        )
        .select_related("investigation")
        .first()
    )
    if not source:
        return {"outcome": "ignored", "reason": "source_not_approved"}
    results = crawl.results or {}
    content = str(results.get("text_snippet") or "")
    raw_payload = {
        "crawl_id": crawl.id,
        "url": crawl.url,
        "title": results.get("title", ""),
        "keyword_hits": results.get("keyword_hits", {}),
        "links": results.get("links", []),
        "status_code": results.get("status_code"),
    }
    digest = _content_hash(content, raw_payload)
    evidence, created = EvidenceItem.objects.get_or_create(
        source=source,
        external_id=f"crawl-{crawl.id}",
        version=1,
        defaults={
            "investigation": source.investigation,
            "kind": EvidenceItem.Kind.ONION_CRAWL,
            "public_url": crawl.url,
            "content": content,
            "normalized_content": evaluate_drug_signal(content).normalized_text,
            "content_hash": digest,
            "raw_payload": raw_payload,
            "occurred_at": crawl.created_at,
        },
    )
    if not created:
        return {"outcome": "duplicate_crawl", "evidence_id": evidence.id}
    _link_evidence_entities(evidence)
    signal = _record_signal(evidence)
    source.last_collected_at = timezone.now()
    source.save(update_fields=["last_collected_at", "updated_at"])
    refresh_correlations(source.investigation_id)
    return {"outcome": "captured", "evidence_id": evidence.id, "signal_id": signal.id if signal else None}


def _record_signal(evidence: EvidenceItem) -> DrugSignal | None:
    result = evaluate_drug_signal(evidence.content)
    if not result.signal_type:
        return None
    signal = DrugSignal.objects.create(
        evidence=evidence,
        investigation=evidence.investigation,
        signal_type=result.signal_type,
        risk_score=result.risk_score,
        matched_terms=result.matched_terms,
        evidence_spans=result.evidence_spans,
        rule_version=RULE_VERSION,
    )
    if signal.risk_score >= 70:
        emit_alert(
            event_type=AlertRule.EventType.DRUG_SIGNAL,
            title=f"High-risk drug-sale signal in {evidence.source.display_name}",
            message=(
                f"Deterministic score {signal.risk_score}/100; analyst review is required "
                "before any escalation."
            ),
            payload={
                "signal_id": signal.id,
                "evidence_id": evidence.id,
                "source_id": evidence.source_id,
                "investigation_id": evidence.investigation_id,
                "risk_score": signal.risk_score,
                "matched_terms": signal.matched_terms,
                "rule_version": signal.rule_version,
            },
            severity=AlertEvent.Severity.HIGH,
            source_key=f"drug-signal:{signal.id}",
            force=True,
        )
    return signal


def refresh_correlations(investigation_id: int | None) -> list[CorrelationFinding]:
    if not investigation_id:
        return []
    repeated = (
        EvidenceEntity.objects.filter(evidence__investigation_id=investigation_id)
        .values("entity_id")
        .annotate(
            source_count=Count("evidence__source", distinct=True),
            evidence_count=Count("evidence", distinct=True),
        )
        .filter(source_count__gte=2)
    )
    findings: list[CorrelationFinding] = []
    for item in repeated:
        entity = Entity.objects.get(pk=item["entity_id"])
        evidence_ids = list(
            EvidenceEntity.objects.filter(
                entity=entity,
                evidence__investigation_id=investigation_id,
            )
            .values_list("evidence_id", flat=True)
            .distinct()
        )
        identity = f"repeated:{investigation_id}:{entity.pk}"
        finding, _ = CorrelationFinding.objects.update_or_create(
            dedupe_key=hashlib.sha256(identity.encode("utf-8")).hexdigest(),
            defaults={
                "investigation_id": investigation_id,
                "title": f"Repeated {entity.get_kind_display().lower()}: {entity.display_name or entity.value}",
                "description": (
                    f"The same indicator appears in {item['source_count']} approved sources and "
                    f"{item['evidence_count']} evidence items. This is a correlation, not an identity claim."
                ),
                "severity": (
                    CorrelationFinding.Severity.HIGH
                    if item["source_count"] >= 3
                    else CorrelationFinding.Severity.MEDIUM
                ),
                "supporting_evidence_ids": evidence_ids,
                "entity_ids": [entity.pk],
            },
        )
        findings.append(finding)
    return findings


def ingest_telegram_update(update: dict[str, Any]) -> dict[str, Any]:
    """Persist an allowlisted Telegram update and create reviewable intelligence.

    Unknown, suspended, and unapproved sources are deliberately ignored. This is
    the primary boundary preventing a webhook from becoming broad collection.
    """

    update_id = update.get("update_id")
    if not isinstance(update_id, int):
        return {"outcome": "ignored", "reason": "missing_update_id"}
    receipt, created = TelegramUpdateReceipt.objects.get_or_create(update_id=update_id)
    if not created:
        return {"outcome": "duplicate_update", "update_id": update_id}

    message, is_edit = _message_from_update(update)
    if not message:
        receipt.outcome = "ignored"
        receipt.detail = {"reason": "unsupported_update"}
        receipt.processed_at = timezone.now()
        receipt.save(update_fields=["outcome", "detail", "processed_at"])
        return {"outcome": "ignored", "reason": "unsupported_update", "update_id": update_id}

    source = _source_for_message(message)
    if not source:
        receipt.outcome = "ignored"
        receipt.detail = {"reason": "source_not_approved"}
        receipt.processed_at = timezone.now()
        receipt.save(update_fields=["outcome", "detail", "processed_at"])
        return {"outcome": "ignored", "reason": "source_not_approved", "update_id": update_id}

    external_id = str(message.get("message_id") or "")
    if not external_id:
        receipt.outcome = "ignored"
        receipt.detail = {"reason": "missing_message_id"}
        receipt.processed_at = timezone.now()
        receipt.save(update_fields=["outcome", "detail", "processed_at"])
        return {"outcome": "ignored", "reason": "missing_message_id", "update_id": update_id}

    content = str(message.get("text") or message.get("caption") or "")
    author = message.get("from") or {}
    author_alias = str(author.get("username") or author.get("id") or "")
    forwarded = message.get("forward_origin") or {}
    forwarded_from = str(forwarded.get("type") or "")
    digest = _content_hash(content, message)

    with transaction.atomic():
        latest = (
            EvidenceItem.objects.select_for_update()
            .filter(source=source, external_id=external_id, is_latest=True)
            .first()
        )
        if latest and latest.content_hash == digest:
            receipt.outcome = "duplicate_message"
            receipt.detail = {"evidence_id": latest.id}
            receipt.processed_at = timezone.now()
            receipt.save(update_fields=["outcome", "detail", "processed_at"])
            return {"outcome": "duplicate_message", "evidence_id": latest.id, "update_id": update_id}
        version = 1
        if latest:
            latest.is_latest = False
            latest.save(update_fields=["is_latest"])
            version = latest.version + 1
        normalized = evaluate_drug_signal(content).normalized_text
        evidence = EvidenceItem.objects.create(
            source=source,
            investigation=source.investigation,
            external_id=external_id,
            version=version,
            author_alias=author_alias,
            reply_to_external_id=str((message.get("reply_to_message") or {}).get("message_id") or ""),
            forwarded_from=forwarded_from,
            content=content,
            normalized_content=normalized,
            content_hash=digest,
            raw_payload=message,
            occurred_at=_occurred_at(message.get("date")),
        )
        _link_evidence_entities(evidence)
        signal = _record_signal(evidence)
        source.latest_cursor = external_id
        source.last_collected_at = timezone.now()
        source.save(update_fields=["latest_cursor", "last_collected_at", "updated_at"])
        receipt.outcome = "edited" if is_edit and version > 1 else "captured"
        receipt.detail = {"evidence_id": evidence.id, "signal_id": signal.id if signal else None}
        receipt.processed_at = timezone.now()
        receipt.save(update_fields=["outcome", "detail", "processed_at"])

    refresh_correlations(source.investigation_id)
    return {
        "outcome": receipt.outcome,
        "update_id": update_id,
        "evidence_id": evidence.id,
        "signal_id": signal.id if signal else None,
    }
