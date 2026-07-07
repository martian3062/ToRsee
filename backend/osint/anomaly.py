"""Tor relay anomaly detection.

Uses PyOD v3's TimeSeriesOD (2026) — it runs any of PyOD's 60+ base detectors
over a sliding window, which is exactly what we want for per-relay bandwidth /
consensus-weight time series. Falls back to a robust z-score if PyOD or the
scientific stack is unavailable, or if a relay has too few observations to fit
a window model.
"""
from __future__ import annotations

import logging
from statistics import median

logger = logging.getLogger(__name__)

# Minimum samples before we bother fitting a windowed detector.
MIN_SAMPLES_FOR_TSOD = 24
DEFAULT_METRIC = "observed_bandwidth"


def _severity_from_score(score: float) -> str:
    if score >= 0.75:
        return "high"
    if score >= 0.5:
        return "medium"
    return "low"


def _zscore_scores(series: list[float]) -> list[float]:
    """Robust (median/MAD) z-score normalized to 0..1. Used as a fallback."""
    n = len(series)
    if n == 0:
        return []
    med = median(series)
    abs_dev = [abs(x - med) for x in series]
    mad = median(abs_dev) or 1e-9
    raw = [abs(0.6745 * (x - med) / mad) for x in series]
    # squash to 0..1 (a z of ~3.5 -> ~0.75)
    return [min(1.0, r / 4.66) for r in raw]


def _pyod_scores(series: list[float], metric: str) -> tuple[list[float], str] | None:
    """Return (normalized_scores, detector_name) using PyOD, or None on failure."""
    try:
        import numpy as np
        from pyod.models.ts_od import TimeSeriesOD
    except Exception as exc:  # pragma: no cover - depends on optional stack
        logger.info("PyOD unavailable, using z-score fallback: %s", exc)
        return None

    try:
        x = np.asarray(series, dtype=float).reshape(-1, 1)
        window = min(50, max(8, len(series) // 3))
        clf = TimeSeriesOD(detector="IForest", window_size=window, step=1, contamination=0.1)
        clf.fit(x)
        raw = np.asarray(clf.decision_scores_, dtype=float)
        # pad back to full length (windowing can shorten the score vector)
        if raw.shape[0] < len(series):
            pad = np.full(len(series) - raw.shape[0], raw[0] if raw.size else 0.0)
            raw = np.concatenate([pad, raw])
        lo, hi = float(raw.min()), float(raw.max())
        span = (hi - lo) or 1e-9
        norm = [float((v - lo) / span) for v in raw]
        return norm, "TimeSeriesOD"
    except Exception as exc:  # pragma: no cover
        logger.warning("TimeSeriesOD failed, falling back to z-score: %s", exc)
        return None


def score_relay_series(observations: list[dict], metric: str = DEFAULT_METRIC) -> dict | None:
    """Score one relay's ordered observations. Returns the flagged anomaly dict
    (for the latest point) or None if nothing anomalous.

    Each observation is a dict with at least the metric key and relay metadata.
    """
    if len(observations) < 4:
        return None

    series = [float(o.get(metric, 0) or 0) for o in observations]
    if max(series) == min(series):
        return None  # flat line, nothing to flag

    detector = "z-score"
    if len(series) >= MIN_SAMPLES_FOR_TSOD:
        pyod_out = _pyod_scores(series, metric)
        if pyod_out is not None:
            scores, detector = pyod_out
        else:
            scores = _zscore_scores(series)
    else:
        scores = _zscore_scores(series)

    latest_score = scores[-1]
    latest = observations[-1]

    # Only surface the latest point if it is genuinely anomalous.
    if latest_score < 0.5 and not (metric == DEFAULT_METRIC and not latest.get("running", True)):
        return None

    # Classify: dropped offline vs traffic spike vs collapse.
    baseline = median(series[:-1]) if len(series) > 1 else series[0]
    current = series[-1]
    if not latest.get("running", True):
        anomaly_type = "relay_offline"
        latest_score = max(latest_score, 0.8)
    elif current > baseline * 1.6:
        anomaly_type = "bandwidth_spike"
    elif current < baseline * 0.4:
        anomaly_type = "bandwidth_collapse"
    else:
        anomaly_type = "consensus_shift" if metric != DEFAULT_METRIC else "bandwidth_anomaly"

    return {
        "fingerprint": latest.get("fingerprint", ""),
        "nickname": latest.get("nickname", ""),
        "country_code": latest.get("country_code", ""),
        "country_name": latest.get("country_name", ""),
        "as_number": latest.get("as_number", ""),
        "latitude": latest.get("latitude"),
        "longitude": latest.get("longitude"),
        "metric": metric,
        "anomaly_type": anomaly_type,
        "score": round(latest_score, 4),
        "severity": _severity_from_score(latest_score),
        "detector": detector,
        "detail": {
            "baseline": round(baseline, 2),
            "current": round(current, 2),
            "samples": len(series),
            "pct_change": round(((current - baseline) / (baseline or 1e-9)) * 100, 1),
        },
    }


def score_relays(series_by_relay: dict[str, list[dict]]) -> list[dict]:
    """Score every relay's series and return sorted anomalies (highest score first)."""
    anomalies: list[dict] = []
    for fingerprint, obs in series_by_relay.items():
        obs_sorted = sorted(obs, key=lambda o: o.get("observed_at", ""))
        for metric in (DEFAULT_METRIC, "consensus_weight"):
            result = score_relay_series(obs_sorted, metric)
            if result:
                anomalies.append(result)
                break  # one anomaly per relay is enough for the dashboard
    anomalies.sort(key=lambda a: a["score"], reverse=True)
    return anomalies
