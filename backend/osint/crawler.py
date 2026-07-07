"""Tor-routed crawler for clearnet and .onion URLs.

Uses httpx over the local Tor SOCKS proxy (socks5h:// so DNS — including .onion
resolution — happens at the proxy) plus BeautifulSoup for extraction. This is
the lightweight default engine; Scrapling / Crawl4AI can be dropped in later as
heavier stealth/JS-rendering backends behind the same interface.
"""
from __future__ import annotations

import logging
from urllib.parse import urljoin, urlparse

import httpx

logger = logging.getLogger(__name__)

_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ToRsy-Crawler/1.0"


def is_onion(url: str) -> bool:
    try:
        return urlparse(url).hostname.endswith(".onion")  # type: ignore[union-attr]
    except Exception:
        return False


def _extract(html: str, base_url: str, keywords: list[str]) -> dict:
    try:
        from bs4 import BeautifulSoup
    except Exception:  # pragma: no cover
        text = html
        title = ""
        links: list[str] = []
    else:
        soup = BeautifulSoup(html, "html.parser")
        title = (soup.title.string or "").strip() if soup.title else ""
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text = " ".join(soup.get_text(" ").split())
        links = []
        for a in soup.find_all("a", href=True):
            href = urljoin(base_url, a["href"])
            if href.startswith("http") and href not in links:
                links.append(href)
        links = links[:50]

    lowered = text.lower()
    keyword_hits = {kw: lowered.count(kw.lower()) for kw in keywords if kw and kw.lower() in lowered}

    return {
        "title": title,
        "text_snippet": text[:1200],
        "text_length": len(text),
        "links": links,
        "link_count": len(links),
        "keyword_hits": keyword_hits,
    }


def _tor_reachable(tor_socks_url: str) -> bool:
    try:
        with httpx.Client(proxy=tor_socks_url, timeout=5.0) as c:
            return c.get("https://check.torproject.org/api/ip").status_code == 200
    except Exception:
        return False


def crawl(url: str, keywords: list[str], tor_socks_url: str = "socks5h://127.0.0.1:9050") -> dict:
    onion = is_onion(url)
    result: dict = {"url": url, "is_onion": onion, "routed_via_tor": False, "keywords": keywords}

    client_kwargs: dict = {"timeout": 30.0, "headers": {"User-Agent": _UA}, "follow_redirects": True}
    # .onion is unreachable without Tor; clearnet uses Tor when the proxy is up.
    if onion or _tor_reachable(tor_socks_url):
        client_kwargs["proxy"] = tor_socks_url
        result["routed_via_tor"] = True
    elif onion:
        result["error"] = "Tor SOCKS proxy not reachable; cannot resolve .onion address."
        return result

    try:
        with httpx.Client(**client_kwargs) as client:
            resp = client.get(url)
            result["status_code"] = resp.status_code
            result["content_type"] = resp.headers.get("content-type", "")
            result.update(_extract(resp.text, url, keywords))
    except Exception as exc:
        result["error"] = str(exc)
    return result
