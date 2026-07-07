from __future__ import annotations

from dataclasses import dataclass

import httpx
from django.conf import settings


class ProviderError(RuntimeError):
    pass


@dataclass
class FetchResult:
    provider: str
    url: str
    title: str
    content_markdown: str
    metadata: dict


class WebFetchService:
    default_chain = ["firecrawl", "zenrows", "bright_data", "tinyfish", "direct"]

    def fetch(self, url: str, preference: list[str] | None = None) -> FetchResult:
        chain = list(preference or []) + [p for p in self.default_chain if p not in (preference or [])]
        errors: list[str] = []
        for provider in chain:
            try:
                if provider == "firecrawl":
                    return self._firecrawl(url)
                if provider == "zenrows":
                    return self._zenrows(url)
                if provider == "bright_data":
                    return self._bright_data(url)
                if provider == "tinyfish":
                    return self._tinyfish(url)
                if provider == "direct":
                    return self._direct(url)
            except ProviderError as exc:
                errors.append(f"{provider}: {exc}")
        raise ProviderError("; ".join(errors) or "no provider could fetch the URL")

    def _mock(self, provider: str, url: str) -> FetchResult:
        return FetchResult(
            provider=provider,
            url=url,
            title=f"Mock capture for {url}",
            content_markdown=(
                f"# Mock capture for {url}\n\n"
                "This deterministic provider response lets ToRsy run without paid API keys. "
                "Replace PROVIDER_MOCK_MODE with false and add keys to call real providers."
            ),
            metadata={"mock": True, "source_provider": provider},
        )

    def _firecrawl(self, url: str) -> FetchResult:
        api_key = settings.PROVIDER_SETTINGS["firecrawl"]["api_key"]
        if settings.PROVIDER_MOCK_MODE:
            return self._mock("firecrawl", url)
        if not api_key:
            raise ProviderError("FIRECRAWL_API_KEY is missing")
        response = httpx.post(
            "https://api.firecrawl.dev/v2/scrape",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"url": url, "formats": ["markdown"]},
            timeout=45,
        )
        response.raise_for_status()
        payload = response.json()
        data = payload.get("data", payload)
        return FetchResult(
            provider="firecrawl",
            url=url,
            title=data.get("metadata", {}).get("title", url),
            content_markdown=data.get("markdown") or data.get("content") or "",
            metadata={"raw": data.get("metadata", {}), "mock": False},
        )

    def _zenrows(self, url: str) -> FetchResult:
        api_key = settings.PROVIDER_SETTINGS["zenrows"]["api_key"]
        if settings.PROVIDER_MOCK_MODE:
            return self._mock("zenrows", url)
        if not api_key:
            raise ProviderError("ZENROWS_API_KEY is missing")
        response = httpx.get(
            "https://api.zenrows.com/v1/",
            params={"apikey": api_key, "url": url, "js_render": "true"},
            timeout=45,
        )
        response.raise_for_status()
        text = response.text
        return FetchResult(
            provider="zenrows",
            url=url,
            title=url,
            content_markdown=text[:20000],
            metadata={"mock": False, "content_type": response.headers.get("content-type")},
        )

    def _bright_data(self, url: str) -> FetchResult:
        api_key = settings.PROVIDER_SETTINGS["bright_data"]["api_key"]
        if settings.PROVIDER_MOCK_MODE:
            return self._mock("bright_data", url)
        if not api_key:
            raise ProviderError("BRIGHT_DATA_API_KEY is missing")
        raise ProviderError("configure a Bright Data collector-specific endpoint before live use")

    def _tinyfish(self, url: str) -> FetchResult:
        api_key = settings.PROVIDER_SETTINGS["tinyfish"]["api_key"]
        if settings.PROVIDER_MOCK_MODE:
            return self._mock("tinyfish", url)
        if not api_key:
            raise ProviderError("TINYFISH_API_KEY is missing")
        raise ProviderError("configure TinyFish Fetch or Agent surface before live use")

    def _direct(self, url: str) -> FetchResult:
        if settings.PROVIDER_MOCK_MODE:
            return self._mock("direct", url)
        response = httpx.get(url, timeout=30, follow_redirects=True)
        response.raise_for_status()
        return FetchResult(
            provider="direct",
            url=str(response.url),
            title=str(response.url),
            content_markdown=response.text[:20000],
            metadata={"mock": False, "content_type": response.headers.get("content-type")},
        )
