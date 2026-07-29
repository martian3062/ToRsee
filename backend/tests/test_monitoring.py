import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from osint.alerts import emit_alert
from osint.models import (
    AlertEvent,
    AlertRule,
    CensorshipIncident,
    MonitoredTarget,
    OSINTScan,
    Snapshot,
)
from osint.monitoring import record_snapshot
from osint.schedules import dispatch_due_monitored_targets


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
def test_monitor_run_now_creates_scan_and_baseline_snapshot(api_client, settings):
    settings.PROVIDER_MOCK_MODE = True
    settings.CELERY_TASK_ALWAYS_EAGER = True

    created = api_client.post(
        "/api/osint/monitors/",
        {
            "kind": "username",
            "value": "target_user",
            "interval": 300,
            "config": {},
        },
        format="json",
    )
    assert created.status_code == 201
    assert created.data["last_run"] is None

    run = api_client.post(f"/api/osint/monitors/{created.data['id']}/run/", {}, format="json")
    assert run.status_code == 202
    assert run.data["dispatch"]["dispatched"] is True
    assert run.data["target"]["last_run"] is not None

    scan = OSINTScan.objects.get(monitored_target_id=created.data["id"])
    assert scan.status == OSINTScan.Status.COMPLETED
    snapshot = Snapshot.objects.get(osint_scan=scan)
    assert snapshot.changed is False
    assert snapshot.previous is None


@pytest.mark.django_db
def test_beat_dispatches_only_due_targets(settings):
    settings.PROVIDER_MOCK_MODE = True
    settings.CELERY_TASK_ALWAYS_EAGER = True
    due = MonitoredTarget.objects.create(
        kind=MonitoredTarget.Kind.USERNAME,
        value="due_user",
        interval=3600,
    )
    MonitoredTarget.objects.create(
        kind=MonitoredTarget.Kind.DOMAIN,
        value="not-due.example",
        interval=3600,
        last_run=timezone.now(),
    )

    result = dispatch_due_monitored_targets()

    assert result["checked"] == 2
    assert result["dispatched"] == 1
    assert OSINTScan.objects.filter(monitored_target=due).count() == 1
    assert OSINTScan.objects.count() == 1


@pytest.mark.django_db
def test_snapshot_diff_emits_change_alert(settings):
    settings.PROVIDER_MOCK_MODE = True
    first = record_snapshot(
        source_type=Snapshot.SourceType.USERNAME,
        target="changing_user",
        payload={"found_accounts": [{"url": "https://example.com/old"}]},
    )
    second = record_snapshot(
        source_type=Snapshot.SourceType.USERNAME,
        target="changing_user",
        payload={
            "found_accounts": [
                {"url": "https://example.com/old"},
                {"url": "https://example.com/new"},
            ]
        },
    )

    assert first.changed is False
    assert second.changed is True
    assert second.diff["accounts_added"] == ["https://example.com/new"]
    event = AlertEvent.objects.get(event_type=AlertRule.EventType.CHANGE)
    assert event.delivered is True
    assert event.payload["snapshot_id"] == second.id


@pytest.mark.django_db
def test_custom_alert_rule_filters_and_deduplicates(settings):
    settings.PROVIDER_MOCK_MODE = True
    rule = AlertRule.objects.create(
        name="Offline relay in AS3320",
        event_type=AlertRule.EventType.RELAY_ANOMALY,
        conditions={"as_number": "AS3320", "anomaly_type": "relay_offline", "min_score": 0.8},
    )
    payload = {
        "as_number": "AS3320",
        "anomaly_type": "relay_offline",
        "score": 0.91,
    }

    first = emit_alert(
        event_type=AlertRule.EventType.RELAY_ANOMALY,
        title="Relay offline",
        message="A watched relay dropped.",
        payload=payload,
        severity=AlertEvent.Severity.HIGH,
        source_key="relay-test-1",
    )
    second = emit_alert(
        event_type=AlertRule.EventType.RELAY_ANOMALY,
        title="Relay offline",
        message="A watched relay dropped.",
        payload=payload,
        severity=AlertEvent.Severity.HIGH,
        source_key="relay-test-1",
    )

    assert len(first) == 1
    assert first[0].rule == rule
    assert second[0].id == first[0].id
    assert AlertEvent.objects.count() == 1


@pytest.mark.django_db
def test_crawl_keyword_hit_creates_snapshot_and_alert(api_client, settings):
    settings.PROVIDER_MOCK_MODE = True
    settings.CELERY_TASK_ALWAYS_EAGER = True

    response = api_client.post(
        "/api/osint/crawl/",
        {"url": "http://exampleforum7g2z.onion/", "keywords": "market,leak"},
        format="json",
    )

    assert response.status_code == 201
    assert Snapshot.objects.filter(source_type=Snapshot.SourceType.CRAWL).count() == 1
    event = AlertEvent.objects.get(event_type=AlertRule.EventType.KEYWORD_HIT)
    assert event.delivered is True
    assert event.payload["keyword_hits"]


@pytest.mark.django_db
def test_repeated_censorship_result_is_not_duplicated(api_client, settings):
    settings.PROVIDER_MOCK_MODE = True
    settings.CELERY_TASK_ALWAYS_EAGER = True
    payload = {"target": "example.com", "scan_type": "domain"}

    assert api_client.post("/api/osint/scan/", payload, format="json").status_code == 201
    assert api_client.post("/api/osint/scan/", payload, format="json").status_code == 201

    assert CensorshipIncident.objects.count() == 1
    assert AlertEvent.objects.filter(event_type=AlertRule.EventType.CENSORSHIP).count() == 1
