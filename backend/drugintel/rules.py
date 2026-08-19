from __future__ import annotations

import html
import re
import unicodedata
from dataclasses import dataclass


RULE_VERSION = "drug-intel-rules-v1"

SUBSTANCE_TERMS = (
    "cocaine",
    "heroin",
    "fentanyl",
    "meth",
    "methamphetamine",
    "mdma",
    "ecstasy",
    "opioid",
    "ketamine",
    "lsd",
)
COMMERCIAL_TERMS = (
    "for sale",
    "available",
    "wholesale",
    "bulk",
    "vendor",
    "menu",
    "stock",
)
DISTRIBUTION_TERMS = (
    "delivery",
    "shipping",
    "worldwide",
    "discreet",
    "drop",
)

HANDLE_RE = re.compile(r"(?<![\w@])@([A-Za-z0-9_]{5,32})")
URL_RE = re.compile(r"https?://[^\s<>()]+", re.IGNORECASE)
ONION_RE = re.compile(r"(?:https?://)?[a-z2-7]{16,56}\.onion(?:/[^\s<>()]*)?", re.IGNORECASE)


@dataclass(frozen=True)
class RuleResult:
    normalized_text: str
    matched_terms: list[str]
    evidence_spans: list[dict]
    risk_score: int
    signal_type: str | None


def normalize_text(value: str) -> str:
    value = html.unescape(value or "")
    value = unicodedata.normalize("NFKC", value)
    value = value.replace("\u200b", "").replace("\ufeff", "")
    return " ".join(value.casefold().split())


def _find_terms(text: str, terms: tuple[str, ...], category: str) -> tuple[list[str], list[dict]]:
    matched: list[str] = []
    spans: list[dict] = []
    for term in terms:
        for match in re.finditer(rf"(?<!\w){re.escape(term)}(?!\w)", text, re.IGNORECASE):
            matched.append(term)
            spans.append({"category": category, "term": term, "start": match.start(), "end": match.end()})
    return matched, spans


def evaluate_drug_signal(content: str) -> RuleResult:
    text = normalize_text(content)
    substances, substance_spans = _find_terms(text, SUBSTANCE_TERMS, "substance")
    commercial, commercial_spans = _find_terms(text, COMMERCIAL_TERMS, "commercial")
    distribution, distribution_spans = _find_terms(text, DISTRIBUTION_TERMS, "distribution")
    handles = list(HANDLE_RE.finditer(text))
    urls = list(URL_RE.finditer(text))
    matched_terms = list(dict.fromkeys([*substances, *commercial, *distribution]))
    spans = [*substance_spans, *commercial_spans, *distribution_spans]
    spans.extend(
        {"category": "contact", "term": match.group(0), "start": match.start(), "end": match.end()}
        for match in [*handles, *urls]
    )

    score = 0
    if substances:
        score += 35
    if commercial:
        score += 35
    if substances and commercial:
        score += 15
    if distribution:
        score += 8
    if handles or urls:
        score += 7
    score = min(score, 100)
    signal_type = "illicit_sale" if substances and commercial else (
        "controlled_substance" if substances else None
    )
    return RuleResult(text, matched_terms, spans, score, signal_type)


def extract_indicators(normalized_text: str) -> list[dict[str, str]]:
    indicators: list[dict[str, str]] = []
    for match in HANDLE_RE.finditer(normalized_text):
        indicators.append({"kind": "telegram_handle", "value": f"@{match.group(1)}"})
    for match in URL_RE.finditer(normalized_text):
        value = match.group(0).rstrip(".,;:!?")
        kind = "onion" if ".onion" in value.casefold() else "url"
        indicators.append({"kind": kind, "value": value})
    for match in ONION_RE.finditer(normalized_text):
        value = match.group(0).rstrip(".,;:!?")
        if not any(item["value"] == value for item in indicators):
            indicators.append({"kind": "onion", "value": value})
    return indicators
