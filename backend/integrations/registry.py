from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings


@dataclass(frozen=True)
class ProviderState:
    key: str
    label: str
    role: str
    status: str
    configured: bool
    mock_mode: bool


PROVIDER_CATALOG = {
    "telegram": ("Telegram Bot API", "alerts and slash commands"),
    "groq": ("Groq", "fast chat, summaries, and JSON extraction"),
    "huggingface": ("Hugging Face", "models and embeddings"),
    "sarvam": ("Sarvam AI", "Indian-language speech and translation"),
    "tabpfn": ("TabPFN", "small tabular predictions"),
    "firecrawl": ("Firecrawl", "primary clean markdown scraping"),
    "zenrows": ("ZenRows", "anti-bot scraping fallback"),
    "bright_data": ("Bright Data", "structured scraper APIs"),
    "tinyfish": ("TinyFish", "agentic web automation"),
    "pexels": ("Pexels", "stock photos and videos"),
    "stitch": ("Google Stitch", "design exploration and UI handoff"),
    "pinecone": ("Pinecone", "vector search index"),
    "supabase": ("Supabase", "hosted Postgres and storage"),
    "onionoo": ("Onionoo API", "Tor relay bandwidth & consensus metrics"),
    "ooni": ("OONI API", "Censorship measurement and network blockages"),
    "socks5_tor": ("Tor SOCKS Proxy", "Secure routing via onion network"),
}


def _is_configured(provider: str, values: dict) -> bool:
    if provider == "tabpfn":
        return bool(values.get("enabled"))
    if provider == "pinecone":
        return bool(values.get("api_key") and values.get("host"))
    if provider == "supabase":
        return bool(values.get("url") and values.get("service_role_key"))
    if provider == "bright_data":
        return bool(values.get("api_key"))
    if provider == "telegram":
        return bool(values.get("token"))
    return bool(values.get("api_key") or values.get("token"))


def provider_states() -> list[ProviderState]:
    states: list[ProviderState] = []
    for key, (label, role) in PROVIDER_CATALOG.items():
        values = settings.PROVIDER_SETTINGS.get(key, {})
        configured = _is_configured(key, values)
        if settings.PROVIDER_MOCK_MODE:
            status = "mocked" if not configured else "configured"
        elif configured:
            status = "configured"
        elif key == "tabpfn":
            status = "disabled"
        else:
            status = "missing_key"
        states.append(
            ProviderState(
                key=key,
                label=label,
                role=role,
                status=status,
                configured=configured,
                mock_mode=settings.PROVIDER_MOCK_MODE,
            )
        )
    return states


def provider_payload() -> list[dict]:
    return [state.__dict__ for state in provider_states()]
