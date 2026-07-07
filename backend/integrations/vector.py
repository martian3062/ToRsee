from __future__ import annotations

import httpx
from django.conf import settings

from ai.providers import HuggingFaceEmbeddings
from sources.models import Document


class VectorIndexService:
    def __init__(self) -> None:
        self.embedder = HuggingFaceEmbeddings()

    def upsert_document(self, document: Document) -> str:
        vector = self.embedder.embed_text(document.content_markdown or document.title)
        vector_id = f"document-{document.pk}"
        config = settings.PROVIDER_SETTINGS["pinecone"]
        if settings.PROVIDER_MOCK_MODE or not (config["api_key"] and config["host"]):
            return vector_id
        response = httpx.post(
            f"{config['host'].rstrip('/')}/vectors/upsert",
            headers={"Api-Key": config["api_key"]},
            json={
                "vectors": [
                    {
                        "id": vector_id,
                        "values": vector,
                        "metadata": {"document_id": document.pk, "url": document.url, "title": document.title},
                    }
                ]
            },
            timeout=45,
        )
        response.raise_for_status()
        return vector_id

    def query(self, query: str, top_k: int = 8) -> list[dict]:
        config = settings.PROVIDER_SETTINGS["pinecone"]
        if settings.PROVIDER_MOCK_MODE or not (config["api_key"] and config["host"]):
            return []
        vector = self.embedder.embed_text(query)
        response = httpx.post(
            f"{config['host'].rstrip('/')}/query",
            headers={"Api-Key": config["api_key"]},
            json={"vector": vector, "topK": top_k, "includeMetadata": True},
            timeout=45,
        )
        response.raise_for_status()
        return response.json().get("matches", [])
