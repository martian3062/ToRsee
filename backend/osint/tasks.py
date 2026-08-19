import logging
import random
from datetime import timedelta

import httpx
from django.conf import settings
from django.utils import timezone

from config.celery import app

from .alerts import emit_alert
from .anomaly import score_relays
from .crawler import crawl as tor_crawl
from .crawler import is_onion
from .monitoring import record_snapshot
from .models import (
    AlertEvent,
    AlertRule,
    CensorshipIncident,
    DarkWebCrawl,
    OSINTScan,
    RelayAnomaly,
    RelayObservation,
)
from .whatsmyname import run_username_scan

logger = logging.getLogger(__name__)

TOR_SOCKS_URL = "socks5h://127.0.0.1:9050"


@app.task(name="osint.run_osint_scan_task")
def run_osint_scan_task(scan_id: int):
    try:
        scan = OSINTScan.objects.get(id=scan_id)
    except OSINTScan.DoesNotExist:
        logger.error(f"OSINTScan {scan_id} not found.")
        return

    scan.status = OSINTScan.Status.RUNNING
    scan.save(update_fields=["status", "updated_at"])

    try:
        if settings.PROVIDER_MOCK_MODE:
            results = generate_mock_results(scan.scan_type, scan.target)
        else:
            results = execute_live_scan(scan.scan_type, scan.target)

        scan.results = results
        scan.status = OSINTScan.Status.COMPLETED
        scan.save(update_fields=["results", "status", "updated_at"])

        if scan.scan_type == OSINTScan.ScanType.USERNAME:
            record_snapshot(
                source_type="username",
                target=scan.target,
                payload=results,
                monitored_target=scan.monitored_target,
                osint_scan=scan,
            )
        # A relay scan also refreshes the monitored time-series + anomaly scores.
        if scan.scan_type == OSINTScan.ScanType.TOR_RELAY:
            run_relay_monitor_task(scan.target, scan.monitored_target_id)
        # A domain scan checks OONI for real censorship signals against that domain.
        if scan.scan_type == OSINTScan.ScanType.DOMAIN:
            refresh_censorship_for_domain(scan.target, scan.monitored_target_id)

    except Exception as exc:
        logger.exception("OSINT scan failed")
        scan.status = OSINTScan.Status.FAILED
        scan.error = str(exc)
        scan.save(update_fields=["status", "error", "updated_at"])


def execute_live_scan(scan_type: str, target: str) -> dict:
    if scan_type == OSINTScan.ScanType.USERNAME:
        return run_username_scan(target, TOR_SOCKS_URL)
    elif scan_type == OSINTScan.ScanType.DOMAIN:
        return run_live_domain_scan(target)
    elif scan_type == OSINTScan.ScanType.METADATA:
        return run_live_metadata_scan(target)
    elif scan_type == OSINTScan.ScanType.TOR_RELAY:
        return run_live_tor_relay_scan(target)
    else:
        raise ValueError(f"Unknown scan type: {scan_type}")


def run_live_domain_scan(domain: str) -> dict:
    import dns.resolver

    results = {"domain": domain, "dns_records": {}, "security_headers": {}, "ip_addresses": []}

    for record_type in ["A", "MX", "TXT", "NS"]:
        try:
            answers = dns.resolver.resolve(domain, record_type)
            results["dns_records"][record_type] = [str(rdata) for rdata in answers]
            if record_type == "A":
                results["ip_addresses"].extend([str(rdata) for rdata in answers])
        except Exception as e:
            results["dns_records"][record_type] = f"Error: {e}"

    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(f"https://{domain}", follow_redirects=True)
            results["status_code"] = resp.status_code
            for header in [
                "content-security-policy",
                "strict-transport-security",
                "x-frame-options",
                "x-content-type-options",
            ]:
                results["security_headers"][header] = resp.headers.get(header, "Missing")
    except Exception as e:
        results["web_check_error"] = str(e)

    return results


def run_live_metadata_scan(target_url_or_path: str) -> dict:
    import os
    from io import BytesIO

    import exifread

    results = {"target": target_url_or_path, "metadata": {}, "has_exif": False}

    content = None
    if target_url_or_path.startswith(("http://", "https://")):
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(target_url_or_path)
                resp.raise_for_status()
                content = resp.content
        except Exception as e:
            results["fetch_error"] = str(e)
    else:
        safe_path = os.path.join(settings.BASE_DIR, target_url_or_path)
        if os.path.exists(safe_path):
            with open(safe_path, "rb") as f:
                content = f.read()
        else:
            results["fetch_error"] = f"File {target_url_or_path} not found"

    if content:
        try:
            tags = exifread.process_file(BytesIO(content), details=False)
            if tags:
                results["has_exif"] = True
                for tag, value in tags.items():
                    results["metadata"][str(tag)] = str(value)
        except Exception as e:
            results["exif_error"] = str(e)
        results["file_size_bytes"] = len(content)

    return results


def run_live_tor_relay_scan(target_relay: str) -> dict:
    results = {"search_term": target_relay, "relays": []}
    url = f"https://onionoo.torproject.org/details?search={target_relay}"
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                for r in data.get("relays", [])[:10]:
                    results["relays"].append(
                        {
                            "nickname": r.get("nickname"),
                            "fingerprint": r.get("fingerprint"),
                            "or_addresses": r.get("or_addresses"),
                            "last_seen": r.get("last_seen"),
                            "running": r.get("running"),
                            "flags": r.get("flags", []),
                            "consensus_weight": r.get("consensus_weight"),
                            "observed_bandwidth": r.get("observed_bandwidth"),
                            "country": r.get("country_name"),
                            "country_code": r.get("country"),
                            "as_number": r.get("as"),
                            "latitude": r.get("latitude"),
                            "longitude": r.get("longitude"),
                        }
                    )
    except Exception as e:
        results["onionoo_error"] = str(e)
    return results


# ---------------------------------------------------------------------------
# Relay monitoring + PyOD anomaly detection
# ---------------------------------------------------------------------------

# A few well-known relay geolocations for realistic demo data.
_DEMO_RELAYS = [
    {"nickname": "FrankfurtExit", "cc": "de", "country": "Germany", "asn": "AS3320", "lat": 50.11, "lon": 8.68, "base_bw": 12_500_000, "cw": 8500},
    {"nickname": "AmsterdamGuard", "cc": "nl", "country": "Netherlands", "asn": "AS16265", "lat": 52.37, "lon": 4.90, "base_bw": 9_800_000, "cw": 6200},
    {"nickname": "ParisMiddle", "cc": "fr", "country": "France", "asn": "AS12876", "lat": 48.86, "lon": 2.35, "base_bw": 4_200_000, "cw": 2100},
    {"nickname": "StockholmExit", "cc": "se", "country": "Sweden", "asn": "AS8473", "lat": 59.33, "lon": 18.06, "base_bw": 15_100_000, "cw": 9900},
    {"nickname": "TorontoGuard", "cc": "ca", "country": "Canada", "asn": "AS16509", "lat": 43.65, "lon": -79.38, "base_bw": 7_400_000, "cw": 4300},
]


def _fingerprint(nickname: str) -> str:
    random.seed(nickname)
    return "".join(random.choice("0123456789ABCDEF") for _ in range(40))


def _build_mock_observations(search_term: str) -> list[dict]:
    """Synthesize ~48h of hourly observations per relay, injecting a real anomaly
    into one relay so the PyOD engine has something genuine to catch."""
    now = timezone.now()
    obs: list[dict] = []
    anomaly_index = random.randint(0, len(_DEMO_RELAYS) - 1)
    for idx, relay in enumerate(_DEMO_RELAYS):
        fp = _fingerprint(relay["nickname"])
        rnd = random.Random(relay["nickname"])
        for h in range(48, 0, -1):
            ts = now - timedelta(hours=h)
            bw = int(relay["base_bw"] * rnd.uniform(0.9, 1.1))
            cw = int(relay["cw"] * rnd.uniform(0.92, 1.08))
            running = True
            # Inject an anomaly in the final few hours of the flagged relay.
            if idx == anomaly_index and h <= 3:
                if anomaly_index % 2 == 0:
                    bw = int(relay["base_bw"] * 2.4)  # bandwidth spike
                else:
                    running = False  # dropped offline
                    bw = 0
            obs.append(
                {
                    "fingerprint": fp,
                    "nickname": relay["nickname"],
                    "country_code": relay["cc"],
                    "country_name": relay["country"],
                    "as_number": relay["asn"],
                    "latitude": relay["lat"],
                    "longitude": relay["lon"],
                    "observed_bandwidth": bw,
                    "consensus_weight": cw,
                    "running": running,
                    "observed_at": ts,
                }
            )
    return obs


def _fetch_onionoo_observations(search_term: str) -> list[dict]:
    """Fetch Onionoo /bandwidth history and fold it into observation rows."""
    obs: list[dict] = []
    detail_url = f"https://onionoo.torproject.org/details?search={search_term}&limit=6"
    bw_url = f"https://onionoo.torproject.org/bandwidth?search={search_term}&limit=6"
    with httpx.Client(timeout=15.0) as client:
        details = {r["fingerprint"]: r for r in client.get(detail_url).json().get("relays", [])}
        bw_doc = client.get(bw_url).json()
    now = timezone.now()
    for relay in bw_doc.get("relays", []):
        fp = relay.get("fingerprint", "")
        meta = details.get(fp, {})
        history = (relay.get("write_history") or {}).get("3_days") or (relay.get("write_history") or {}).get("1_month")
        if not history:
            continue
        factor = history.get("factor", 1.0)
        values = history.get("values", [])
        interval = history.get("interval", 3600)
        first = now - timedelta(seconds=interval * len(values))
        for i, v in enumerate(values):
            if v is None:
                continue
            obs.append(
                {
                    "fingerprint": fp,
                    "nickname": meta.get("nickname", ""),
                    "country_code": meta.get("country", ""),
                    "country_name": meta.get("country_name", ""),
                    "as_number": meta.get("as", ""),
                    "latitude": meta.get("latitude"),
                    "longitude": meta.get("longitude"),
                    "observed_bandwidth": int(v * factor),
                    "consensus_weight": meta.get("consensus_weight", 0) or 0,
                    "running": meta.get("running", True),
                    "observed_at": first + timedelta(seconds=interval * i),
                }
            )
    return obs


def run_relay_monitor_task(search_term: str = "", monitored_target_id: int | None = None) -> dict:
    """Ingest relay time-series, run PyOD anomaly detection, persist anomalies."""
    if settings.PROVIDER_MOCK_MODE:
        observations = _build_mock_observations(search_term)
    else:
        try:
            observations = _fetch_onionoo_observations(search_term)
        except Exception as exc:
            logger.warning("Onionoo history fetch failed: %s", exc)
            observations = []

    if not observations:
        return {"observations": 0, "anomalies": 0}

    # Persist raw observations (keep table bounded to the latest run per relay set).
    fps = {o["fingerprint"] for o in observations}
    RelayObservation.objects.filter(fingerprint__in=fps).delete()
    RelayObservation.objects.bulk_create(
        [RelayObservation(**o) for o in observations], batch_size=500
    )

    # Group into per-relay series and score.
    series_by_relay: dict[str, list[dict]] = {}
    for o in observations:
        series_by_relay.setdefault(o["fingerprint"], []).append(o)

    anomalies = score_relays(series_by_relay)

    # Refresh anomaly records for this relay set.
    RelayAnomaly.objects.filter(fingerprint__in=fps).delete()
    for a in anomalies:
        anomaly = RelayAnomaly.objects.create(**a)
        if anomaly.severity == RelayAnomaly.Severity.HIGH:
            payload = {
                "anomaly_id": anomaly.id,
                "fingerprint": anomaly.fingerprint,
                "nickname": anomaly.nickname,
                "country_code": anomaly.country_code,
                "as_number": anomaly.as_number,
                "anomaly_type": anomaly.anomaly_type,
                "metric": anomaly.metric,
                "score": anomaly.score,
                "severity": anomaly.severity,
                "detail": anomaly.detail,
            }
            emit_alert(
                event_type=AlertRule.EventType.RELAY_ANOMALY,
                title=f"High-severity relay anomaly: {anomaly.nickname or anomaly.fingerprint[:8]}",
                message=(
                    f"{anomaly.anomaly_type.replace('_', ' ')} in "
                    f"{anomaly.as_number or anomaly.country_code or 'unknown network'} "
                    f"(score {anomaly.score:.2f})."
                ),
                payload=payload,
                severity=AlertEvent.Severity.HIGH,
                source_key=(
                    f"relay:{anomaly.fingerprint}:{anomaly.anomaly_type}:"
                    f"{anomaly.detected_at:%Y%m%d%H}"
                ),
                monitored_target_id=monitored_target_id,
                force=True,
            )

    return {"observations": len(observations), "anomalies": len(anomalies)}


def _create_censorship_incident(
    *,
    domain: str,
    country_code: str,
    asn: str,
    anomaly_type: str,
    measurement_count: int,
    failure_rate: float,
    monitored_target_id: int | None,
) -> bool:
    recent_cutoff = timezone.now() - timedelta(hours=24)
    duplicate = CensorshipIncident.objects.filter(
        country_code=country_code,
        asn=asn,
        target_domain=domain,
        anomaly_type=anomaly_type,
        measurement_count=measurement_count,
        failure_rate=failure_rate,
        reported_at__gte=recent_cutoff,
    ).exists()
    if duplicate:
        return False

    incident = CensorshipIncident.objects.create(
        country_code=country_code,
        asn=asn,
        target_domain=domain,
        anomaly_type=anomaly_type,
        measurement_count=measurement_count,
        failure_rate=failure_rate,
    )
    emit_alert(
        event_type=AlertRule.EventType.CENSORSHIP,
        title=f"New censorship signal for {domain}",
        message=(
            f"{anomaly_type} in {country_code}"
            f"{f' / {asn}' if asn else ''}: {failure_rate:.0%} anomaly rate "
            f"across {measurement_count} measurements."
        ),
        payload={
            "incident_id": incident.id,
            "country_code": country_code,
            "asn": asn,
            "target_domain": domain,
            "anomaly_type": anomaly_type,
            "measurement_count": measurement_count,
            "failure_rate": failure_rate,
        },
        severity=AlertEvent.Severity.HIGH if failure_rate >= 0.5 else AlertEvent.Severity.MEDIUM,
        source_key=f"censorship:{incident.id}",
        monitored_target_id=monitored_target_id,
        force=True,
    )
    return True


def refresh_censorship_for_domain(
    domain: str,
    monitored_target_id: int | None = None,
) -> int:
    """Query OONI for real web_connectivity anomalies against the domain.

    In mock mode (or when OONI is unreachable) we record a clearly-labelled
    demo incident instead of silently fabricating one on every domain.
    """
    if not settings.PROVIDER_MOCK_MODE:
        try:
            url = (
                "https://api.ooni.io/api/v1/aggregation"
                f"?domain={domain}&test_name=web_connectivity&axis_x=probe_cc"
            )
            with httpx.Client(timeout=15.0) as client:
                groups = client.get(url).json().get("result", [])
            created = 0
            for g in groups:
                measurements = g.get("measurement_count", 0) or 0
                anomalies = g.get("anomaly_count", 0) or 0
                if measurements and anomalies and anomalies / measurements > 0.2:
                    created += int(
                        _create_censorship_incident(
                            domain=domain,
                            country_code=g.get("probe_cc", "??"),
                            asn="",
                            anomaly_type="web_connectivity anomaly (OONI)",
                            measurement_count=measurements,
                            failure_rate=round(anomalies / measurements, 3),
                            monitored_target_id=monitored_target_id,
                        )
                    )
            return created
        except Exception as exc:
            logger.warning("OONI fetch failed: %s", exc)

    # Demo fallback — explicitly labelled so it is not mistaken for live data.
    return int(
        _create_censorship_incident(
            domain=domain,
            country_code="IR",
            asn="AS12880",
            anomaly_type="DNS Tampering (demo)",
            measurement_count=145,
            failure_rate=0.92,
            monitored_target_id=monitored_target_id,
        )
    )


# ---------------------------------------------------------------------------
# Dark-web / onion crawler
# ---------------------------------------------------------------------------


@app.task(name="osint.run_darkweb_crawl_task")
def run_darkweb_crawl_task(crawl_id: int):
    try:
        record = DarkWebCrawl.objects.get(id=crawl_id)
    except DarkWebCrawl.DoesNotExist:
        logger.error("DarkWebCrawl %s not found", crawl_id)
        return

    record.status = DarkWebCrawl.Status.RUNNING
    record.save(update_fields=["status", "updated_at"])

    keywords = [k.strip() for k in (record.keywords or "").split(",") if k.strip()]
    try:
        if settings.PROVIDER_MOCK_MODE:
            results = _mock_crawl(record.url, keywords)
        else:
            results = tor_crawl(record.url, keywords, TOR_SOCKS_URL)

        record.results = results
        record.routed_via_tor = results.get("routed_via_tor", False)
        record.is_onion = results.get("is_onion", is_onion(record.url))
        record.status = (
            DarkWebCrawl.Status.FAILED if results.get("error") else DarkWebCrawl.Status.COMPLETED
        )
        if results.get("error"):
            record.error = results["error"]
        record.save()

        if record.status == DarkWebCrawl.Status.COMPLETED:
            from drugintel.services import ingest_onion_crawl

            ingest_onion_crawl(record)
            snapshot = record_snapshot(
                source_type="crawl",
                target=record.url,
                payload=results,
                monitored_target=record.monitored_target,
                darkweb_crawl=record,
            )
            keyword_hits = {
                keyword: int(count)
                for keyword, count in (results.get("keyword_hits") or {}).items()
                if int(count) > 0
            }
            if keyword_hits and (snapshot.previous_id is None or snapshot.changed):
                emit_alert(
                    event_type=AlertRule.EventType.KEYWORD_HIT,
                    title=f"Watched keyword found at {record.url}",
                    message=", ".join(
                        f"{keyword}: {count}" for keyword, count in keyword_hits.items()
                    ),
                    payload={
                        "crawl_id": record.id,
                        "target": record.url,
                        "keyword_hits": keyword_hits,
                        "snapshot_id": snapshot.id,
                    },
                    severity=AlertEvent.Severity.HIGH,
                    source_key=f"crawl-keywords:{snapshot.id}",
                    monitored_target=record.monitored_target,
                    force=True,
                )
    except Exception as exc:
        logger.exception("crawl failed")
        record.status = DarkWebCrawl.Status.FAILED
        record.error = str(exc)
        record.save(update_fields=["status", "error", "updated_at"])


def _mock_crawl(url: str, keywords: list[str]) -> dict:
    onion = is_onion(url)
    hits = {kw: random.randint(1, 6) for kw in keywords[:3]}
    return {
        "url": url,
        "is_onion": onion,
        "routed_via_tor": True,
        "status_code": 200,
        "content_type": "text/html",
        "title": "Hidden Wiki — Directory" if onion else "Sample Page",
        "text_snippet": (
            "Welcome to the directory. Listings include marketplaces, forums, and "
            "paste sites. This is mock content generated in PROVIDER_MOCK_MODE so the "
            "crawler UI can be demoed without touching the live Tor network."
        ),
        "text_length": 4820,
        "links": [
            "http://msydqstlz2kzerdg.onion/",
            "http://zqktlwiuavvvqqt4ybvgvi7tyo4hjl5xgfuvpdf6otjiycgwqbym2qad.onion/wiki/",
            "http://exampleforum7g2z.onion/threads/",
        ]
        if onion
        else ["https://example.com/about", "https://example.com/contact"],
        "link_count": 3 if onion else 2,
        "keyword_hits": hits,
    }


# ---------------------------------------------------------------------------
# Mock scan results (unchanged shapes, extended relay geo fields)
# ---------------------------------------------------------------------------


def generate_mock_results(scan_type: str, target: str) -> dict:
    if scan_type == OSINTScan.ScanType.USERNAME:
        found = [
            {"platform": "GitHub", "url": f"https://github.com/{target}", "category": "coding"},
            {"platform": "Reddit", "url": f"https://www.reddit.com/user/{target}/about.json", "category": "social"},
            {"platform": "Medium", "url": f"https://medium.com/@{target}", "category": "blog"},
            {"platform": "Keybase", "url": f"https://keybase.io/{target}", "category": "coding"},
        ]
        details = [
            {"platform": "GitHub", "category": "coding", "url": f"https://github.com/{target}", "status_code": 200, "found": True},
            {"platform": "GitLab", "category": "coding", "url": f"https://gitlab.com/{target}", "status_code": 404, "found": False},
            {"platform": "Reddit", "category": "social", "url": f"https://www.reddit.com/user/{target}/about.json", "status_code": 200, "found": True},
            {"platform": "Instagram", "category": "social", "url": f"https://www.instagram.com/{target}/", "status_code": 404, "found": False},
            {"platform": "Medium", "category": "blog", "url": f"https://medium.com/@{target}", "status_code": 200, "found": True},
            {"platform": "Keybase", "category": "coding", "url": f"https://keybase.io/{target}", "status_code": 200, "found": True},
            {"platform": "Twitch", "category": "gaming", "url": f"https://m.twitch.tv/{target}", "status_code": 404, "found": False},
            {"platform": "SoundCloud", "category": "music", "url": f"https://soundcloud.com/{target}", "status_code": 404, "found": False},
        ]
        return {
            "username": target,
            "sites_checked": 24,
            "routed_via_tor": True,
            "found_accounts": found,
            "scan_details": details,
        }
    elif scan_type == OSINTScan.ScanType.DOMAIN:
        return {
            "domain": target,
            "ip_addresses": ["104.244.42.1", "104.244.42.129"],
            "dns_records": {
                "A": ["104.244.42.1", "104.244.42.129"],
                "MX": ["10 mail.protonmail.ch", "20 mailsec.protonmail.ch"],
                "TXT": ["v=spf1 include:_spf.protonmail.ch ~all", "google-site-verification=mock123"],
                "NS": ["dns1.registrar-servers.com", "dns2.registrar-servers.com"],
            },
            "security_headers": {
                "content-security-policy": "default-src 'self' https:; script-src 'self' 'unsafe-inline';",
                "strict-transport-security": "max-age=63072000; includeSubDomains; preload",
                "x-frame-options": "DENY",
                "x-content-type-options": "nosniff",
            },
            "status_code": 200,
        }
    elif scan_type == OSINTScan.ScanType.METADATA:
        return {
            "target": target,
            "has_exif": True,
            "file_size_bytes": 1048576,
            "metadata": {
                "Image Make": "Apple",
                "Image Model": "iPhone 15 Pro",
                "Image DateTime": "2026:07:06 14:32:05",
                "EXIF ExifImageWidth": "4032",
                "EXIF ExifImageLength": "3024",
                "GPS GPSLatitudeRef": "N",
                "GPS GPSLatitude": "[37, 46, 30]",
                "GPS GPSLongitudeRef": "W",
                "GPS GPSLongitude": "[122, 25, 5]",
                "Software": "iOS 17.5",
            },
        }
    elif scan_type == OSINTScan.ScanType.TOR_RELAY:
        return {
            "search_term": target,
            "relays": [
                {
                    "nickname": f"{target}Node",
                    "fingerprint": "A1B2C3D4E5F678901234567890ABCDEF12345678",
                    "or_addresses": ["192.0.2.55:9001"],
                    "last_seen": "2026-07-06T18:00:00Z",
                    "running": True,
                    "flags": ["Exit", "Fast", "Guard", "Running", "Stable", "Valid"],
                    "consensus_weight": 8500,
                    "observed_bandwidth": 12500000,
                    "country": "Germany",
                    "country_code": "de",
                    "as_number": "AS3320",
                    "latitude": 50.11,
                    "longitude": 8.68,
                },
                {
                    "nickname": f"Shadow{target}",
                    "fingerprint": "1234567890ABCDEF1234567890ABCDEF12345678",
                    "or_addresses": ["198.51.100.11:9001"],
                    "last_seen": "2026-07-06T15:30:00Z",
                    "running": False,
                    "flags": ["Running", "Valid"],
                    "consensus_weight": 120,
                    "observed_bandwidth": 450000,
                    "country": "Netherlands",
                    "country_code": "nl",
                    "as_number": "AS16265",
                    "latitude": 52.37,
                    "longitude": 4.90,
                },
            ],
        }
    return {}
