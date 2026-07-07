"""WhatsMyName-style username enumeration.

Replaces the old naive status-code check with per-site match/no-match
signatures (existence code + existence string / missing code + missing string)
to sharply cut false positives. Sites are checked concurrently and, when the
local Tor SOCKS proxy is reachable, requests egress through it.
"""
from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

_RULES_PATH = Path(__file__).resolve().parent / "data" / "whatsmyname.json"
_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ToRsy-OSINT/1.0"


def load_sites() -> list[dict]:
    try:
        data = json.loads(_RULES_PATH.read_text(encoding="utf-8"))
        return data.get("sites", [])
    except Exception as exc:  # pragma: no cover
        logger.error("Failed to load whatsmyname ruleset: %s", exc)
        return []


def _classify(site: dict, status_code: int, body: str, account: str) -> bool | None:
    """Return True (found), False (absent), or None (indeterminate)."""
    e_code = site.get("e_code")
    m_code = site.get("m_code")
    e_string = (site.get("e_string") or "").replace("{account}", account)
    m_string = site.get("m_string") or ""

    # A missing signature is the strongest negative signal.
    if m_code is not None and status_code == m_code and m_string and m_string in body:
        return False
    # Existence signature: right status code AND expected string present.
    if e_code is not None and status_code == e_code:
        if not e_string or e_string in body:
            return True
    if status_code == 404:
        return False
    return None


def _probe(client: httpx.Client, site: dict, account: str) -> dict:
    url = site["uri_check"].replace("{account}", account)
    entry = {"platform": site["name"], "category": site.get("cat", ""), "url": url}
    try:
        resp = client.get(url, follow_redirects=True)
        body = resp.text or ""
        verdict = _classify(site, resp.status_code, body, account)
        entry.update({"status_code": resp.status_code, "found": bool(verdict)})
        if verdict is None:
            entry["found"] = False
            entry["indeterminate"] = True
    except Exception as exc:
        entry.update({"error": str(exc), "found": False})
    return entry


def _tor_reachable(tor_socks_url: str) -> bool:
    try:
        with httpx.Client(proxy=tor_socks_url, timeout=4.0) as c:
            return c.get("https://check.torproject.org/api/ip").status_code == 200
    except Exception:
        return False


def run_username_scan(username: str, tor_socks_url: str = "socks5h://127.0.0.1:9050") -> dict:
    sites = load_sites()
    results = {
        "username": username,
        "sites_checked": len(sites),
        "found_accounts": [],
        "scan_details": [],
        "routed_via_tor": False,
    }

    client_kwargs: dict = {
        "timeout": 8.0,
        "headers": {"User-Agent": _UA},
    }
    if _tor_reachable(tor_socks_url):
        client_kwargs["proxy"] = tor_socks_url
        results["routed_via_tor"] = True

    details: list[dict] = []
    with httpx.Client(**client_kwargs) as client:
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = {pool.submit(_probe, client, site, username): site for site in sites}
            for fut in as_completed(futures):
                details.append(fut.result())

    details.sort(key=lambda d: d["platform"])
    results["scan_details"] = details
    results["found_accounts"] = [
        {"platform": d["platform"], "url": d["url"], "category": d.get("category", "")}
        for d in details
        if d.get("found")
    ]
    return results
