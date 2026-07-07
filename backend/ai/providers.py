from __future__ import annotations

import hashlib
from dataclasses import dataclass

import httpx
from django.conf import settings


@dataclass
class AIResult:
    text: str
    model: str
    provider: str
    metadata: dict


class GroqSummarizer:
    def summarize(self, text: str, prompt: str = "") -> AIResult:
        config = settings.PROVIDER_SETTINGS["groq"]
        model = config["model"]
        clean_text = " ".join(text.split())
        if settings.PROVIDER_MOCK_MODE or not config["api_key"]:
            snippet = clean_text[:420] or "No content was available."
            return AIResult(
                text=f"Mock summary: {snippet}",
                model=model,
                provider="groq",
                metadata={"mock": True},
            )
        response = httpx.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {config['api_key']}"},
            json={
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": "Summarize web research content into concise operator notes.",
                    },
                    {"role": "user", "content": f"{prompt}\n\n{text[:12000]}"},
                ],
                "temperature": 0.2,
            },
            timeout=45,
        )
        response.raise_for_status()
        payload = response.json()
        return AIResult(
            text=payload["choices"][0]["message"]["content"],
            model=model,
            provider="groq",
            metadata={"mock": False, "usage": payload.get("usage", {})},
        )


class HuggingFaceEmbeddings:
    dimension = 64

    def embed_text(self, text: str) -> list[float]:
        config = settings.PROVIDER_SETTINGS["huggingface"]
        if settings.PROVIDER_MOCK_MODE or not config["token"]:
            digest = hashlib.sha256(text.encode("utf-8")).digest()
            values = []
            while len(values) < self.dimension:
                for byte in digest:
                    values.append((byte / 127.5) - 1.0)
                    if len(values) == self.dimension:
                        break
            return values
        response = httpx.post(
            f"https://api-inference.huggingface.co/pipeline/feature-extraction/{config['embed_model']}",
            headers={"Authorization": f"Bearer {config['token']}"},
            json={"inputs": text[:4000]},
            timeout=45,
        )
        response.raise_for_status()
        payload = response.json()
        if payload and isinstance(payload[0], list):
            payload = payload[0]
        return [float(value) for value in payload[: self.dimension]]


class SarvamSpeechService:
    def status(self) -> dict:
        config = settings.PROVIDER_SETTINGS["sarvam"]
        return {
            "configured": bool(config["api_key"]),
            "model": config["tts_model"],
            "mock_mode": settings.PROVIDER_MOCK_MODE,
        }


class TabPFNService:
    def status(self) -> dict:
        configured = bool(settings.PROVIDER_SETTINGS["tabpfn"]["enabled"])
        available = False
        if configured:
            try:
                __import__("tabpfn")
                available = True
            except Exception:
                available = False
        return {"configured": configured, "available": available}
