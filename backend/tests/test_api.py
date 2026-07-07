import pytest
from rest_framework.test import APIClient

from integrations.registry import provider_payload
from jobs.models import IngestionJob
from sources.models import Document


@pytest.fixture
def api_client():
    return APIClient()


def test_provider_registry_exposes_expected_services(settings):
    settings.PROVIDER_MOCK_MODE = True
    keys = {provider["key"] for provider in provider_payload()}
    assert {"telegram", "groq", "huggingface", "firecrawl", "pinecone", "supabase"}.issubset(keys)


@pytest.mark.django_db
def test_health_endpoint(api_client):
    response = api_client.get("/api/health")
    assert response.status_code == 200
    assert response.data["status"] == "ok"
    assert response.data["providers"]


@pytest.mark.django_db
def test_ingest_flow_creates_job_document_and_summary(api_client, settings):
    settings.PROVIDER_MOCK_MODE = True
    response = api_client.post(
        "/api/jobs/ingest",
        {
            "urls": ["https://example.com/research"],
            "provider_preference": ["firecrawl"],
            "tags": ["demo", "research"],
            "notify": True,
        },
        format="json",
    )
    assert response.status_code == 201
    assert response.data["status"] == IngestionJob.Status.COMPLETED
    assert response.data["targets"][0]["document"]["title"].startswith("Mock capture")
    assert Document.objects.count() == 1


@pytest.mark.django_db
def test_search_and_summarize(api_client, settings):
    settings.PROVIDER_MOCK_MODE = True
    ingest = api_client.post(
        "/api/jobs/ingest",
        {"urls": ["https://example.com/searchable"], "provider_preference": ["firecrawl"]},
        format="json",
    )
    document_id = ingest.data["targets"][0]["document"]["id"]

    search = api_client.post("/api/search", {"query": "deterministic", "top_k": 3}, format="json")
    assert search.status_code == 200
    assert search.data["local_matches"]

    summary = api_client.post("/api/ai/summarize", {"document_ids": [document_id]}, format="json")
    assert summary.status_code == 200
    assert summary.data["summary"].startswith("Mock summary")


@pytest.mark.django_db
def test_telegram_webhook_commands(api_client, settings):
    settings.PROVIDER_MOCK_MODE = True
    response = api_client.post(
        "/api/telegram/webhook",
        {"message": {"chat": {"id": 123}, "text": "/status"}},
        format="json",
    )
    assert response.status_code == 200
    assert response.data["command"] == "status"
    assert "ToRsy jobs" in response.data["text"]
