from __future__ import annotations

from django.db.models import Q

from sources.models import Document

from .vector import VectorIndexService


class SearchService:
    def search(self, query: str, top_k: int = 8) -> dict:
        vector_matches = VectorIndexService().query(query, top_k=top_k)
        local_docs = Document.objects.filter(
            Q(title__icontains=query) | Q(content_markdown__icontains=query) | Q(url__icontains=query)
        )[:top_k]
        local_matches = [
            {
                "id": doc.pk,
                "title": doc.title,
                "url": doc.url,
                "snippet": (doc.content_markdown or "")[:320],
                "embedding_id": doc.embedding_id,
                "source": "local",
            }
            for doc in local_docs
        ]
        return {"query": query, "vector_matches": vector_matches, "local_matches": local_matches}
