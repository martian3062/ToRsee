# ToRsy — Future Roadmap 🗺️

_What ToRsy can grow into. This is a living backlog, ordered by leverage. Each item
notes the touch-points in the current codebase so it can be picked up cold._

Legend: 🟢 quick win (≤1 day) · 🟡 medium (a few days) · 🔴 large (week+) ·
⭐ highest leverage

---

## 0. Where we are today

Already shipped and verified:

- Web ingestion + semantic search (provider fetch chain, Groq summaries, vector index).
- OSINT scans: username (WhatsMyName ruleset), domain (DNS + headers), metadata (EXIF).
- Tor relay scan (Onionoo) + **PyOD `TimeSeriesOD` anomaly detection** with geo/severity.
- OONI censorship cockpit.
- Tor-routed dark-web crawler (`socks5h://` + BeautifulSoup).
- Reagraph footprint graph + MapLibre anomaly map.
- Continuous monitoring with Celery Beat, snapshot diffs, alert rules, and Telegram
  delivery audit.
- Live monitoring updates over SSE with TanStack Query caching and polling fallback.
- Python 3.12, Tailwind CSS 4, generated OpenAPI/TypeScript contracts, and a
  PostgreSQL 18 extension-ready local stack.
- 19 backend tests green, frontend builds clean, and GitHub Actions enforces both.

The roadmap below extends from that baseline.

---

## 1. Turn one-shot scans into continuous monitoring ⭐

**Shipped 2026-07-29.** ToRsy can now *watch* things from the Continuous Monitoring
dashboard and REST API.

- ✅ **Celery Beat schedules.** `MonitoredTarget` supports username, domain, OONI,
  relay, and onion watches; `osint/schedules.py` claims due work once per minute.
- ✅ **Change detection + diffing.** SHA-256 snapshots record username/crawl baselines
  and structured account, keyword, and field changes.
- ✅ **Anomaly → alert fan-out.** High-severity relay anomalies, new censorship
  incidents, crawl keyword hits, and detected changes flow to Telegram with an
  auditable, deduplicated `AlertEvent`.
- ✅ **Alert rules engine.** Rules can be global or target-scoped, support exact,
  minimum, maximum, keyword, and contains conditions, plus cooldowns.

---

## 2. The correlation engine (the thesis piece) 🔴⭐

The first governed implementation now correlates repeated Telegram handles, URLs, and
onion references across evidence in an `Investigation`; every relationship preserves its
supporting evidence and is explicitly labelled as correlation rather than identity proof.

- 🔴 **Cross-signal correlation.** Join `RelayAnomaly` (by country/ASN) with
  `CensorshipIncident` (same country/ASN) and crawl keyword-hits over the same window.
  Surface "relay drop-off in AS_X coincides with censorship spike in AS_X" cards.
- ✅ **Telegram evidence and triage.** Approved source registry, versioned message evidence,
  deterministic drug-sale signals, human decisions, and high-risk Telegram alerts.
- 🟡 **Entity graph / investigations.** Extend the current Telegram entity base to group
  scans, crawls, relays, and domains in a shared graph across *all* entity types.
- 🟡 **Timeline view.** A unified chronological feed of every event in an investigation
  (Recharts/visx time-series with anomaly overlays).

---

## 3. Deepen each existing module

### Username / identity 🟢🟡
- 🟢 **Expand the ruleset** from 24 to the full ~600-site WhatsMyName list (drop-in JSON;
  `osint/data/whatsmyname.json`).
- 🟡 **Email intelligence.** Add holehe-style account-existence checks and a **Have I Been
  Pwned** breach lookup (an HIBP MCP connector is already available in this environment —
  just needs authorizing).
- 🟡 **Confidence scoring.** Return a 0–1 confidence per hit instead of a boolean, using
  redirect chains + content length + the `indeterminate` flag already emitted by
  `whatsmyname._classify`.

### Domain / attack surface 🟡
- 🟡 **Subdomain enumeration** via crt.sh certificate transparency + optional BBOT.
- 🟡 **Passive DNS history** and **Shodan/Censys** port/banner exposure.
- 🟢 **WHOIS + registrar + TLS cert parsing** into the domain result card.

### Metadata / OpSec 🟢
- 🟢 **PDF support** with `pdfplumber` (author, software, creation tool leaks).
- 🟢 **GPS → decimal + map pin.** Decode the EXIF GPS tuples into lat/lon and drop a
  MapLibre marker (reuse `relay-map.tsx`). Touch: `osint/tasks.run_live_metadata_scan`.
- 🟡 **Batch/bulk metadata** across a crawled site's downloadable documents.

### Tor / network 🟡🔴
- 🟡 **`stem` circuit visualization.** Use the control port (9051) to build/inspect a
  circuit and render entry → middle → exit hops on the map.
- 🟡 **Richer Onionoo history** — pull `/uptime` and `/weights` alongside `/bandwidth`;
  score multiple metrics per relay instead of one.
- 🔴 **Model upgrades.** Try `dtaianomaly` per-relay baselines and the 2026 eigenspace-
  alignment method (arxiv 2605.20391) for structural network anomalies; A/B against the
  current `TimeSeriesOD`. Touch: `osint/anomaly.py` (already pluggable via `detector`).

### Dark-web crawler 🟡🔴
- 🟡 **Scrapling / Crawl4AI backends.** The crawler is built behind a clean `crawl()`
  interface — add stealth/JS-rendering engines for onion sites that need a browser.
  (Heavy: pulls Playwright + browsers; gate behind an extra.)
- 🟡 **Recursive crawl + frontier.** Follow discovered `.onion` links to a depth limit
  with a visited-set and politeness delays.
- 🟢 **Feed crawl text into the AI pipeline.** Route `text_snippet` through the existing
  Groq summarizer + Pinecone index so onion content is searchable alongside clearnet.

---

## 4. AI / LLM layer

- 🟡 **Investigation copilot.** An agent that, given a target, plans and runs the right
  scans, then writes a narrative intelligence report (Markdown → PDF export).
- 🟢 **Auto-summary of anomalies.** Groq-generated plain-English explanation per
  `RelayAnomaly` / correlation card.
- 🟡 **RAG over collected intel.** Extend semantic search to cover scan results and crawl
  text, not just ingested documents.

---

## 5. Platform, security & ops (needed before this leaves the lab) 🔴

ToRsy has a Tor egress and stores investigation data — it needs guardrails once it is
more than a local demo.

- 🔴 **AuthN/Z + multi-tenant.** DRF auth (token/JWT), per-user investigations, and an
  audit log of who scanned what. The drug-intelligence endpoints already require an
  operator key outside mock mode; replace that bootstrap gate with user roles before
  shared deployment.
- 🟡 **Rate limiting + scope allowlist** on live scans; **pagination + filtering** on
  scan/incident/anomaly/crawl endpoints.
- 🟡 **Ethics & legality guardrails.** Consent/authorization prompts, a target allowlist,
  and clear "authorized use only" gating for live mode.
- 🟢 **Structured logging + Sentry** for the Celery tasks.
- ✅ **CI pipeline.** GitHub Actions runs pytest, ruff, migration/schema drift checks,
  generated TypeScript contract drift, type-checking, and `next build`.
- 🟡 **Deployment.** Containerize backend + frontend; a `docker-compose.prod.yml`;
  Netlify/Vercel for the frontend (connectors available in this environment).

---

## 6. Frontend / UX

- 🟢 **Dark mode + theme** matching the "buddy in the dark" identity.
- 🟡 **Recharts time-series** for relay bandwidth/uptime history with anomaly bands.
- 🟡 **deck.gl arc layer** over MapLibre for circuit hops / relay-to-relay flows.
- 🟢 **Export** — per-investigation JSON/CSV/PDF report download.
- 🟢 **Rename cleanup.** Propagate **ToRsy** into `package.json` / `pyproject.toml`
  metadata and (optionally) service/DB names; today only docs + UI title are renamed.
- ✅ **Live status.** SSE invalidates the TanStack Query monitoring cache immediately;
  automatic reconnect and 30-second polling cover interrupted streams.

---

## 7. Data & integrations

- 🟡 **Real OONI depth** — the aggregation call exists; add per-measurement drill-down and
  a country/ASN choropleth on the MapLibre map.
- 🟡 **MISP / STIX export** so findings feed threat-intel platforms.
- 🟢 **Bright Data / TinyFish live paths** wired through for clearnet at scale.
- 🟡 **Notion / Google Drive report sync** (connectors available in this environment) so
  investigations export to a shared workspace.

---

## Suggested sequencing

1. ✅ **Continuous monitoring (§1)** — shipped 2026-07-29.
2. **Correlation engine + investigations (§2)** — the differentiator.
3. **Module depth (§3)** — pick per demo need (email/HIBP, subdomains, GPS map).
4. **Auth & ops (§5)** — before any shared/hosted deployment.
5. **AI copilot + reports (§4, §6 export)** — turns raw data into deliverables.

> Anything in here is a self-contained next step. Start with §1 — it converts ToRsy from
> a scanner you drive into a buddy that watches the dark for you.

_ToRsy — your buddy in the dark._ 🕶️
