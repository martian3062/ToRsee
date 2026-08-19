import pytest
from rest_framework.test import APIClient

from drugintel.models import (
    CorrelationFinding,
    DrugSignal,
    EvidenceItem,
    IntelligenceSource,
    TelegramUpdateReceipt,
)


@pytest.fixture
def api_client():
    return APIClient()


def _update(update_id: int, chat_id: int, message_id: int, text: str, *, edited: bool = False):
    return {
        "update_id": update_id,
        "edited_channel_post" if edited else "channel_post": {
            "message_id": message_id,
            "date": 1_726_000_000,
            "chat": {"id": chat_id, "title": "Approved public channel"},
            "from": {"id": 42, "username": "source_author"},
            "text": text,
        },
    }


@pytest.mark.django_db
def test_telegram_collection_creates_versioned_evidence_signal_and_correlation(api_client, settings):
    settings.PROVIDER_MOCK_MODE = True
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.TELEGRAM_COLLECTION_ENABLED = True

    investigation = api_client.post(
        "/api/intel/investigations/",
        {"name": "Approved Telegram investigation", "authorization_reference": "case-001"},
        format="json",
    )
    assert investigation.status_code == 201

    source_payload = {
        "investigation": investigation.data["id"],
        "platform": "telegram",
        "display_name": "Approved source one",
        "collection_mode": "bot_webhook",
        "authorization_status": "approved",
        "enabled": True,
        "interval": 300,
    }
    first_source = api_client.post(
        "/api/intel/sources/",
        {**source_payload, "external_id": "-1001001"},
        format="json",
    )
    second_source = api_client.post(
        "/api/intel/sources/",
        {**source_payload, "external_id": "-1001002", "display_name": "Approved source two"},
        format="json",
    )
    assert first_source.status_code == 201
    assert second_source.status_code == 201

    first = api_client.post(
        "/api/telegram/webhook",
        _update(101, -1001001, 1, "Fentanyl available for sale. Delivery via @sharedvendor."),
        format="json",
    )
    assert first.status_code == 200
    assert first.data["collection"]["outcome"] == "queued"
    assert EvidenceItem.objects.count() == 1
    signal = DrugSignal.objects.get()
    assert signal.risk_score >= 70
    assert signal.review_status == DrugSignal.ReviewStatus.NEW
    assert "fentanyl" in signal.matched_terms

    duplicate = api_client.post(
        "/api/telegram/webhook",
        _update(101, -1001001, 1, "Fentanyl available for sale. Delivery via @sharedvendor."),
        format="json",
    )
    assert duplicate.status_code == 200
    assert EvidenceItem.objects.count() == 1
    assert TelegramUpdateReceipt.objects.count() == 1

    edited = api_client.post(
        "/api/telegram/webhook",
        _update(102, -1001001, 1, "Fentanyl wholesale menu available. Contact @sharedvendor.", edited=True),
        format="json",
    )
    assert edited.status_code == 200
    assert EvidenceItem.objects.filter(external_id="1").count() == 2
    assert EvidenceItem.objects.get(external_id="1", version=1).is_latest is False
    assert EvidenceItem.objects.get(external_id="1", version=2).is_latest is True

    second = api_client.post(
        "/api/telegram/webhook",
        _update(103, -1001002, 3, "Fentanyl for sale. Reach @sharedvendor for availability."),
        format="json",
    )
    assert second.status_code == 200
    correlations = api_client.post(
        f"/api/intel/investigations/{investigation.data['id']}/correlate/",
        {},
        format="json",
    )
    assert correlations.status_code == 200
    assert CorrelationFinding.objects.filter(investigation_id=investigation.data["id"]).exists()

    review = api_client.post(
        f"/api/intel/signals/{signal.id}/review/",
        {"status": "triaged", "reviewer": "analyst-1", "note": "Needs corroboration."},
        format="json",
    )
    assert review.status_code == 200
    signal.refresh_from_db()
    assert signal.review_status == DrugSignal.ReviewStatus.TRIAGED
    assert signal.reviewed_by == "analyst-1"


@pytest.mark.django_db
def test_unapproved_telegram_source_is_ignored(api_client, settings):
    settings.PROVIDER_MOCK_MODE = True
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.TELEGRAM_COLLECTION_ENABLED = True
    IntelligenceSource.objects.create(
        platform=IntelligenceSource.Platform.TELEGRAM,
        external_id="-1002001",
        display_name="Pending source",
        collection_mode=IntelligenceSource.CollectionMode.BOT_WEBHOOK,
        authorization_status=IntelligenceSource.AuthorizationStatus.PENDING,
        enabled=True,
    )

    response = api_client.post(
        "/api/telegram/webhook",
        _update(201, -1002001, 1, "Fentanyl for sale."),
        format="json",
    )
    assert response.status_code == 200
    assert EvidenceItem.objects.count() == 0
    receipt = TelegramUpdateReceipt.objects.get(update_id=201)
    assert receipt.outcome == "ignored"
    assert receipt.detail["reason"] == "source_not_approved"


@pytest.mark.django_db
def test_approved_onion_crawl_enters_shared_evidence_ledger(api_client, settings):
    settings.PROVIDER_MOCK_MODE = True
    settings.CELERY_TASK_ALWAYS_EAGER = True
    investigation = api_client.post(
        "/api/intel/investigations/",
        {"name": "Dark-web evidence"},
        format="json",
    )
    assert investigation.status_code == 201
    IntelligenceSource.objects.create(
        investigation_id=investigation.data["id"],
        platform=IntelligenceSource.Platform.ONION,
        external_id="http://exampleforum7g2z.onion/",
        display_name="Approved onion source",
        collection_mode=IntelligenceSource.CollectionMode.MANUAL,
        authorization_status=IntelligenceSource.AuthorizationStatus.APPROVED,
        enabled=True,
    )

    response = api_client.post(
        "/api/osint/crawl/",
        {"url": "http://exampleforum7g2z.onion/", "keywords": "market,leak"},
        format="json",
    )
    assert response.status_code == 201
    evidence = EvidenceItem.objects.get(kind=EvidenceItem.Kind.ONION_CRAWL)
    assert evidence.investigation_id == investigation.data["id"]
    assert evidence.content_hash


@pytest.mark.django_db
def test_live_mode_requires_operator_and_signed_webhook(api_client, settings):
    settings.PROVIDER_MOCK_MODE = False
    settings.INTELLIGENCE_LIVE_ENABLED = True
    settings.INTELLIGENCE_OPERATOR_KEY = "operator-key"
    settings.TELEGRAM_COLLECTION_ENABLED = False
    settings.PROVIDER_SETTINGS = {
        **settings.PROVIDER_SETTINGS,
        "telegram": {**settings.PROVIDER_SETTINGS["telegram"], "webhook_secret": "webhook-secret"},
    }

    denied = api_client.post("/api/intel/investigations/", {"name": "Denied"}, format="json")
    assert denied.status_code == 403

    allowed = api_client.post(
        "/api/intel/investigations/",
        {"name": "Authorized"},
        format="json",
        HTTP_X_TORSY_OPERATOR_KEY="operator-key",
    )
    assert allowed.status_code == 201

    unsigned = api_client.post(
        "/api/telegram/webhook",
        _update(301, -1003001, 1, "ordinary post"),
        format="json",
    )
    assert unsigned.status_code == 403

    signed = api_client.post(
        "/api/telegram/webhook",
        _update(302, -1003001, 1, "ordinary post"),
        format="json",
        HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN="webhook-secret",
    )
    assert signed.status_code == 200
    assert signed.data["collection"]["outcome"] == "disabled"
