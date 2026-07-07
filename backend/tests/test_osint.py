import pytest
from rest_framework.test import APIClient

from osint.models import OSINTScan


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
def test_create_osint_scan_trigger(api_client, settings):
    settings.PROVIDER_MOCK_MODE = True
    settings.CELERY_TASK_ALWAYS_EAGER = True
    response = api_client.post(
        "/api/osint/scan/",
        {
            "target": "target_user",
            "scan_type": "username"
        },
        format="json"
    )
    assert response.status_code == 201
    assert response.data["status"] == "completed"  # Runs eagerly
    assert response.data["target"] == "target_user"
    assert response.data["scan_type"] == "username"
    assert response.data["results"]["username"] == "target_user"
    assert len(response.data["results"]["found_accounts"]) > 0

    # Test listing scans
    list_response = api_client.get("/api/osint/scan/")
    assert list_response.status_code == 200
    assert len(list_response.data) == 1


@pytest.mark.django_db
def test_censorship_endpoint(api_client, settings):
    settings.PROVIDER_MOCK_MODE = True
    settings.CELERY_TASK_ALWAYS_EAGER = True
    
    # Trigger a scan that seeds anomalies
    response = api_client.post(
        "/api/osint/scan/",
        {
            "target": "example.com",
            "scan_type": "domain"
        },
        format="json"
    )
    assert response.status_code == 201
    
    # Verify the censorship list exposes seeded items
    censorship_response = api_client.get("/api/osint/censorship/")
    assert censorship_response.status_code == 200
    assert len(censorship_response.data) > 0
    assert censorship_response.data[0]["target_domain"] == "example.com"


@pytest.mark.django_db
def test_relay_anomaly_engine_flags_injected_anomaly(api_client, settings):
    settings.PROVIDER_MOCK_MODE = True
    settings.CELERY_TASK_ALWAYS_EAGER = True

    # A tor_relay scan also runs the PyOD monitor and persists anomalies.
    scan = api_client.post(
        "/api/osint/scan/",
        {"target": "FrankfurtExit", "scan_type": "tor_relay"},
        format="json",
    )
    assert scan.status_code == 201

    resp = api_client.get("/api/osint/anomalies/")
    assert resp.status_code == 200
    assert len(resp.data) >= 1
    top = resp.data[0]
    assert 0.0 <= top["score"] <= 1.0
    assert top["severity"] in {"low", "medium", "high"}
    assert top["anomaly_type"] in {
        "bandwidth_spike",
        "bandwidth_collapse",
        "relay_offline",
        "bandwidth_anomaly",
        "consensus_shift",
    }
    # Anomaly rows carry geo so the map can plot them.
    assert top["latitude"] is not None and top["longitude"] is not None


@pytest.mark.django_db
def test_relay_monitor_post_trigger(api_client, settings):
    settings.PROVIDER_MOCK_MODE = True
    resp = api_client.post("/api/osint/anomalies/", {"search": "exit"}, format="json")
    assert resp.status_code == 201
    assert resp.data["summary"]["observations"] > 0


@pytest.mark.django_db
def test_darkweb_crawl_mock(api_client, settings):
    settings.PROVIDER_MOCK_MODE = True
    settings.CELERY_TASK_ALWAYS_EAGER = True

    resp = api_client.post(
        "/api/osint/crawl/",
        {"url": "http://exampleforum7g2z.onion/", "keywords": "market,leak"},
        format="json",
    )
    assert resp.status_code == 201
    assert resp.data["status"] == "completed"
    assert resp.data["is_onion"] is True
    assert resp.data["results"]["link_count"] >= 1


def test_whatsmyname_ruleset_loads():
    from osint.whatsmyname import load_sites

    sites = load_sites()
    assert len(sites) >= 20
    assert all("uri_check" in s and "name" in s for s in sites)
