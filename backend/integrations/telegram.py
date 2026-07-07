from __future__ import annotations

import httpx
from django.conf import settings

from integrations.search import SearchService
from jobs.models import IngestionJob


class TelegramClient:
    def send_message(self, text: str, chat_id: str | None = None) -> dict:
        config = settings.PROVIDER_SETTINGS["telegram"]
        destination = chat_id or config["default_chat_id"]
        if settings.PROVIDER_MOCK_MODE or not (config["token"] and destination):
            return {"ok": True, "mock": True, "chat_id": destination, "text": text}
        response = httpx.post(
            f"https://api.telegram.org/bot{config['token']}/sendMessage",
            json={"chat_id": destination, "text": text},
            timeout=20,
        )
        response.raise_for_status()
        return response.json()


class TelegramCommandRouter:
    def handle_update(self, update: dict) -> dict:
        message = update.get("message") or update.get("edited_message") or {}
        chat = message.get("chat") or {}
        text = (message.get("text") or "").strip()
        chat_id = str(chat.get("id") or "")
        response = self.handle_text(text)
        TelegramClient().send_message(response["text"], chat_id=chat_id)
        return {"chat_id": chat_id, **response}

    def handle_text(self, text: str) -> dict:
        if text.startswith("/status"):
            total = IngestionJob.objects.count()
            latest = IngestionJob.objects.order_by("-created_at").first()
            latest_text = f"latest={latest.status} {latest.id}" if latest else "latest=none"
            return {"command": "status", "text": f"ToRsy jobs: total={total}, {latest_text}"}
        if text.startswith("/search"):
            query = text.removeprefix("/search").strip()
            if not query:
                return {"command": "search", "text": "Usage: /search <query>"}
            results = SearchService().search(query, top_k=3)["local_matches"]
            if not results:
                return {"command": "search", "text": f"No local matches for {query}."}
            lines = [f"- {item['title'] or item['url']}" for item in results]
            return {"command": "search", "text": "Matches:\n" + "\n".join(lines)}
        if text.startswith("/summarize"):
            query = text.removeprefix("/summarize").strip()
            if not query:
                return {"command": "summarize", "text": "Usage: /summarize <query>"}
            results = SearchService().search(query, top_k=1)["local_matches"]
            if not results:
                return {"command": "summarize", "text": f"No document found for {query}."}
            return {"command": "summarize", "text": results[0]["snippet"] or "Document has no text."}
        return {
            "command": "help",
            "text": "Commands: /status, /search <query>, /summarize <query>",
        }
