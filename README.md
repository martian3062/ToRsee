# ToRsy: The Buddy in the Dark

**ToRsy** is a Django + Next.js **OSINT & Tor network intelligence cockpit**. Point it
at a URL, a username, a domain, a file, or a Tor relay and it fetches, enriches,
correlates, and visualizes — mapping both the **network layer** (relay anomalies,
censorship events) and the **application/identity layer** (digital footprints,
metadata leaks, dark-web mentions) in one dashboard.

> Everything runs in **mock mode by default**, so the whole cockpit is safe to demo
> offline without spending API credits or touching the live Tor network.

---

## Table of contents

- [Capabilities](#capabilities)
- [Stack](#stack)
- [High-level architecture](#high-level-architecture)
- [Module data flows](#module-data-flows)
- [API surface](#api-surface)
- [Data model](#data-model)
- [Quick start](#quick-start)
- [Configuration](#configuration)
- [Verification](#verification)
- [Project layout](#project-layout)

---

## Capabilities

| Domain                    | Module                            | What it does                                                                          | Engine                                                              |
| :------------------------ | :-------------------------------- | :------------------------------------------------------------------------------------ | :------------------------------------------------------------------ |
| **Ingest & Search** | Web ingestion                     | Fetch → normalize → summarize → embed → index → alert                            | Firecrawl / ZenRows / Bright Data / TinyFish / Groq / HF / Pinecone |
| **Identity**        | Username footprint                | Enumerate a handle across 24+ platforms with per-site match/no-match signatures       | WhatsMyName-style ruleset                                           |
| **Identity**        | Domain attack surface             | DNS records + HTTP security-header audit                                              | dnspython / httpx                                                   |
| **OpSec**           | Metadata auditor                  | EXIF/GPS/author leaks from images & documents                                         | exifread                                                            |
| **Network**         | Tor relay scan                    | Live relay consensus lookup                                                           | Onionoo                                                             |
| **Network**         | **Relay anomaly detection** | Per-relay bandwidth/consensus time-series scored for spikes, collapses, and drop-offs | **PyOD v3 `TimeSeriesOD`**                                  |
| **Network**         | Censorship cockpit                | Web-connectivity anomalies by country/ASN                                             | OONI Aggregation API                                                |
| **Dark web**        | Onion crawler                     | Crawl`.onion`/clearnet through the Tor SOCKS proxy, extract text/links/keyword hits | httpx + BeautifulSoup over`socks5h://`                            |
| **Monitoring**      | Continuous watch + alerts         | Re-run targets on a cadence, diff snapshots, evaluate rules, and fan alerts to Telegram | Celery Beat / Django / SHA-256                                      |
| **Drug intelligence** | Governed Telegram evidence       | Capture only approved Telegram sources, preserve versioned evidence, flag deterministic sale signals, and route analyst review | Bot webhook / Celery / SHA-256 / rules engine                       |

Visualization: **Reagraph** (WebGL footprint graph), **MapLibre GL** (relay/anomaly geo-map),
plus native tables and meters.

---

## Stack

- **Backend:** Python 3.12, Django 5.2 LTS, Django REST Framework, Celery, Redis, pytest.
- **Anomaly / ML:** PyOD v3, scikit-learn, numpy, scipy.
- **OSINT libs:** stem, dnspython, exifread, beautifulsoup4, httpx + socksio (SOCKS5).
- **Frontend:** Next.js 16, React 19, TypeScript, TanStack Query, Tailwind CSS 4, lucide-react.
- **Visualization:** reagraph (WebGL graph), maplibre-gl (vector maps).
- **API contract:** drf-spectacular OpenAPI schema + generated TypeScript declarations.
- **Infra:** PostgreSQL 18 with TimescaleDB, PostGIS, and pgvector; Redis; Tor SOCKS proxy.
- **Providers (pluggable, all mockable):** Telegram, Groq, Hugging Face, Firecrawl, ZenRows, Bright Data, TinyFish, Pinecone, Supabase, Sarvam, TabPFN, Pexels.

---

## High-level architecture

```mermaid
graph TD
    subgraph Frontend["Next.js Frontend (:3000)"]
        UI[Dashboard — 5 tabs]
        UI --> G[Reagraph WebGL footprint]
        UI --> M[MapLibre relay/anomaly map]
        UI --> T[Tables / meters / doc viewer]
    end

    subgraph Backend["Django REST API (:8000)"]
        API[/api/*]
        API --> JOBS[jobs app — ingestion]
        API --> OSINT[osint app — scans/anomalies/crawl]
        API --> AI[ai app — summarize]
        API --> INT[integrations — health/search/telegram]
        JOBS --> CEL[(Celery + Redis)]
        OSINT --> CEL
    end

    subgraph Engines["Analysis engines"]
        CEL --> FETCH[Fetch chain: Firecrawl→ZenRows→BrightData→TinyFish→direct]
        CEL --> PYOD[PyOD TimeSeriesOD anomaly engine]
        CEL --> WMN[WhatsMyName username enumeration]
        CEL --> CRAWL[Tor SOCKS crawler]
    end

    subgraph External["External sources"]
        FETCH --> WEB[(Clearnet)]
        PYOD --> ONIONOO[(Onionoo history)]
        CRAWL --> TOR[Tor proxy 9050]
        TOR --> ONION[(.onion services)]
        OSINT --> OONI[(OONI API)]
        AI --> GROQ[(Groq / HF)]
        JOBS --> PINE[(Pinecone)]
    end

    Backend --> DB[(Postgres / SQLite)]
    Frontend -->|REST + monitoring SSE| Backend
```

---

## Module data flows

### 1. Web ingestion & semantic search

```mermaid
sequenceDiagram
    participant UI as Dashboard
    participant API as /api/jobs/ingest
    participant CEL as Celery
    participant P as Provider chain
    participant DB as Postgres
    participant V as Pinecone
    participant TG as Telegram
    UI->>API: POST {urls, provider_preference, tags, notify}
    API->>DB: create IngestionJob + JobTargets
    API->>CEL: run job (eager locally)
    CEL->>P: Firecrawl→ZenRows→BrightData→TinyFish→direct
    P-->>CEL: clean markdown
    CEL->>DB: store Document + summary (Groq)
    CEL->>V: upsert embeddings (HF); else local index
    CEL->>TG: job-complete alert (or mock)
    UI->>API: POST /api/search {query} → local + vector matches
```

### 2. Username footprint (WhatsMyName)

```mermaid
sequenceDiagram
    participant UI as OSINT Scanner
    participant API as /api/osint/scan
    participant CEL as Celery
    participant TOR as Tor SOCKS (optional)
    participant S as 24+ platforms
    UI->>API: POST {target, scan_type: username}
    API->>CEL: run_osint_scan_task
    CEL->>TOR: probe reachability → route if up
    CEL->>S: concurrent GET per site (ThreadPool)
    S-->>CEL: status + body
    CEL->>CEL: classify via e_code/e_string vs m_code/m_string
    CEL-->>UI: {sites_checked, found_accounts, scan_details, routed_via_tor}
    UI->>UI: render Reagraph footprint graph
```

### 3. Tor relay anomaly detection (PyOD)

```mermaid
sequenceDiagram
    participant UI as Relay Anomalies tab
    participant API as /api/osint/anomalies
    participant MON as run_relay_monitor_task
    participant OO as Onionoo (bandwidth+details)
    participant PY as PyOD TimeSeriesOD
    participant DB as RelayObservation / RelayAnomaly
    UI->>API: POST {search}
    API->>MON: ingest + score
    MON->>OO: fetch per-relay history (live) / synth (mock)
    MON->>DB: bulk_create RelayObservation (time-series)
    MON->>PY: score each relay series (sliding window)
    PY-->>MON: normalized 0..1 anomaly scores
    MON->>MON: classify offline / spike / collapse / consensus_shift
    MON->>DB: persist RelayAnomaly (geo + severity)
    API-->>UI: anomalies → MapLibre markers + table
```

Fallback: if PyOD/the scientific stack is unavailable or a relay has too few
samples, a robust median/MAD **z-score** is used instead (reported in the
`detector` field).

### 4. Dark-web / onion crawl

```mermaid
sequenceDiagram
    participant UI as Dark Web Crawler tab
    participant API as /api/osint/crawl
    participant CEL as run_darkweb_crawl_task
    participant TOR as Tor proxy 9050
    participant SITE as .onion / clearnet
    UI->>API: POST {url, keywords}
    API->>CEL: crawl
    CEL->>TOR: socks5h:// (DNS + .onion resolved at proxy)
    TOR->>SITE: GET
    SITE-->>CEL: HTML
    CEL->>CEL: BeautifulSoup → title, text, links, keyword hits
    CEL-->>UI: {routed_via_tor, is_onion, keyword_hits, links, text_snippet}
```

### 5. Censorship cockpit (OONI)

A `domain` scan triggers `refresh_censorship_for_domain`, which queries the OONI
Aggregation API for `web_connectivity` anomalies grouped by `probe_cc`, records any
country/ASN whose anomaly rate exceeds 20%, and renders them as an incident table
plus regional blocking-ratio meters. In mock mode a clearly-labelled `(demo)`
incident is written instead of fabricating live-looking data.

### 6. Drug intelligence and approved Telegram sources

```mermaid
sequenceDiagram
    participant TG as Approved Telegram source
    participant WH as Signed webhook
    participant INTEL as Drug intelligence service
    participant DB as Evidence ledger
    participant UI as Analyst triage
    TG->>WH: channel/group update
    WH->>INTEL: queue only when collection is enabled
    INTEL->>INTEL: allowlist source, dedupe update, version edits
    INTEL->>DB: evidence hash, indicators, deterministic signal
    DB->>UI: triage queue and correlation findings
    UI->>DB: reviewer decision and audit history
```

Telegram collection is disabled by default. It accepts only approved Bot-API sources
registered by numeric chat ID; unknown, pending, and suspended sources are ignored.
Live mode requires Telegram's webhook secret and an operator key for intelligence API
actions. This component does not send Telegram evidence to AI, embedding, or vector
providers. Secret Chats, private-content bypasses, and automatic source joining are out
of scope.

---

## API surface

| Method       | Endpoint                   | Body / notes                                                        |
| :----------- | :------------------------- | :------------------------------------------------------------------ |
| `GET`      | `/api/health`            | DB, Redis, provider readiness                                       |
| `GET`      | `/api/schema/`           | generated OpenAPI 3 contract                                        |
| `GET`      | `/api/docs/`             | interactive Swagger UI                                              |
| `GET`      | `/api/jobs/`             | latest ingestion jobs + targets + documents                         |
| `GET`      | `/api/jobs/{id}`         | one job                                                             |
| `POST`     | `/api/jobs/ingest`       | `{ urls, provider_preference, tags, notify }`                     |
| `POST`     | `/api/search`            | `{ query, top_k }` → vector + local matches                      |
| `POST`     | `/api/ai/summarize`      | `{ text }` or `{ document_ids }`                                |
| `GET/POST` | `/api/osint/scan/`       | `{ target, scan_type }` — `username\|domain\|metadata\|tor_relay` |
| `GET`      | `/api/osint/censorship/` | OONI censorship incidents                                           |
| `GET`      | `/api/osint/anomalies/`  | flagged relay anomalies                                             |
| `POST`     | `/api/osint/anomalies/`  | `{ search }` → run PyOD monitor, return summary + anomalies      |
| `GET/POST` | `/api/osint/crawl/`      | `{ url, keywords }` — Tor-routed crawl                           |
| `GET/POST` | `/api/osint/monitors/`   | scheduled username/domain/OONI/relay/onion targets                    |
| `POST`     | `/api/osint/monitors/{id}/run/` | dispatch one target immediately                             |
| `GET`      | `/api/osint/snapshots/`  | crawl and username baselines + structured diffs                       |
| `GET/POST` | `/api/osint/alert-rules/` | exact, `min_`, `max_`, keyword, and `_contains` conditions        |
| `GET`      | `/api/osint/alert-events/` | auditable Telegram delivery log                                      |
| `GET`      | `/api/osint/events/stream/` | live monitoring cache-invalidation stream (SSE)                    |
| `POST`     | `/api/telegram/webhook`  | Telegram Bot update (`/status`, `/search`, `/summarize`)      |
| `GET/POST` | `/api/intel/investigations/` | governed cases, authorization reference, priority                |
| `POST`     | `/api/intel/investigations/{id}/correlate/` | refresh repeated-indicator findings                   |
| `GET/POST` | `/api/intel/sources/` | approved Telegram / evidence-source registry                       |
| `POST`     | `/api/intel/sources/{id}/run/` | mock collection trigger or live webhook-state check            |
| `GET`      | `/api/intel/evidence/` | versioned, hashable evidence ledger                               |
| `GET`      | `/api/intel/signals/` | deterministic drug-sale triage queue                              |
| `POST`     | `/api/intel/signals/{id}/review/` | human review decision and note                              |
| `GET`      | `/api/intel/entities/` | provenance-backed source, handle, URL, and onion indicators       |
| `GET`      | `/api/intel/correlations/` | repeated-indicator findings by investigation                    |

---

## Data model

| App         | Model                                         | Purpose                                         |
| :---------- | :-------------------------------------------- | :---------------------------------------------- |
| `sources` | `Source`                                    | origin metadata                                 |
| `jobs`    | `IngestionJob`, `JobTarget`, `Document` | ingestion pipeline + parsed content             |
| `osint`   | `OSINTScan`                                 | username/domain/metadata/relay scan record      |
| `osint`   | `CensorshipIncident`                        | OONI web-connectivity anomaly                   |
| `osint`   | `RelayObservation`                          | per-relay metric time-series row                |
| `osint`   | `RelayAnomaly`                              | PyOD-scored anomaly (geo + severity + detector) |
| `osint`   | `DarkWebCrawl`                              | Tor-routed crawl result                         |
| `osint`   | `MonitoredTarget`, `Snapshot`               | scheduled watches + change history              |
| `osint`   | `AlertRule`, `AlertEvent`                   | rule filters + delivery audit                   |
| `drugintel` | `Investigation`, `IntelligenceSource` | authorized cases and source registry              |
| `drugintel` | `EvidenceItem`, `DrugSignal` | versioned evidence, deterministic score, human triage |
| `drugintel` | `Entity`, `EvidenceEntity`, `EntityRelationship`, `CorrelationFinding` | provenance-backed network correlation |

---

## Quick start

```powershell
Copy-Item .env.example .env
.\scripts\use-e-cache.ps1                       # pin venv + caches to E:\cache\ToRsy
docker compose -f infra/docker-compose.yml up -d # PostgreSQL 18 + Redis + Tor proxy
cd backend
uv sync --locked --dev                         # managed Python 3.12 under E:\cache
uv run python manage.py migrate
uv run python manage.py runserver 127.0.0.1:8000
```

In another terminal:

```powershell
.\scripts\use-e-cache.ps1
cd frontend
npm install
npm run dev
```

Open **http://localhost:3000** (backend at **http://127.0.0.1:8000**). Provider calls
run in mock mode by default. For no-Docker smoke tests, leave `DATABASE_URL` unset and
Django falls back to SQLite.

For continuous monitoring outside eager local mode, set
`CELERY_TASK_ALWAYS_EAGER=false`, then run the worker and Beat in separate backend
terminals:

```powershell
uv run celery -A config worker --pool=solo --loglevel=info
uv run celery -A config beat --loglevel=info
```

Beat checks once per minute and dispatches only targets whose stored interval has
elapsed. The dashboard also offers **Run now**, pause/resume controls, snapshot diffs,
rule management, and the alert delivery log. TanStack Query refreshes those views from
the SSE stream, with a 30-second polling fallback if the stream is interrupted.

The PostgreSQL container initializes TimescaleDB, PostGIS, and pgvector in a dedicated
`torsy_pg18_data` volume. `GET /api/health` reports the active database engine and
installed extensions. SQLite remains the zero-infrastructure test/demo fallback.

If `8000` is occupied, run Django on another port and start Next with:

```powershell
$env:NEXT_PUBLIC_API_BASE_URL="http://127.0.0.1:8025/api"
npm run dev -- --hostname 127.0.0.1 --port 3000
```

---

## Configuration

Copy `.env.example` to `.env` and set keys only for providers you want live.

| Var                          | Default                       | Meaning                                               |
| :--------------------------- | :---------------------------- | :---------------------------------------------------- |
| `PROVIDER_MOCK_MODE`       | `true`                      | mock all provider + live scan calls                   |
| `CELERY_TASK_ALWAYS_EAGER` | `true`                      | run Celery tasks in-process locally                   |
| `DATABASE_URL`             | SQLite fallback               | `postgres://torsy:torsy@127.0.0.1:5432/torsy`       |
| `REDIS_URL`                | `redis://127.0.0.1:6379/0`  | Celery broker                                         |
| `NEXT_PUBLIC_API_BASE_URL` | `http://127.0.0.1:8000/api` | frontend → backend                                   |
| `TELEGRAM_COLLECTION_ENABLED` | `false` | accepts allowlisted Telegram updates only when enabled |
| `INTELLIGENCE_LIVE_ENABLED` | `false` | permits live intelligence operations with an operator key |
| `INTELLIGENCE_OPERATOR_KEY` | empty | required in `X-ToRsy-Operator-Key` outside mock mode |

Live mode (`PROVIDER_MOCK_MODE=false`) requires the Tor container up for username
routing and onion crawling; relay anomalies then pull real Onionoo history and
censorship pulls the real OONI API.

> **Wallet-extension note:** a MetaMask/wallet browser extension injects `inpage.js`
> into every page and can throw a harmless "MetaMask not found" error. ToRsy uses no
> web3; `layout.tsx` includes a guard that suppresses extension-sourced errors from the
> dev overlay. Real app errors still surface.

---

## Verification

```powershell
.\scripts\use-e-cache.ps1
cd backend
uv run ruff check .
uv run python manage.py spectacular --file ..\docs\openapi.yaml --validate
uv run pytest            # 19 tests, including SSE, schema, monitoring, rules, and dedupe
cd ..\frontend
npm run api:types        # refresh the typed SDK/query bindings from the backend contract
npm run typecheck
npm run build
npm audit                # expected: 0 vulnerabilities
```

---

## Project layout

```
backend/
  osint/
    models.py        scans, crawls, monitored targets, snapshots, alert rules/events
    tasks.py         scans, relay/OONI monitoring, crawl tasks, snapshots, alert fan-out
    schedules.py     due-target claiming + Celery Beat dispatch
    monitoring.py    stable hashes + structured change diffs
    alerts.py        rule evaluation, dedupe, cooldowns, Telegram delivery
    anomaly.py       PyOD TimeSeriesOD engine + z-score fallback
    whatsmyname.py   concurrent per-site username enumeration
    crawler.py       Tor SOCKS crawler (httpx + BeautifulSoup)
    events.py        ASGI-friendly monitoring Server-Sent Events stream
    data/whatsmyname.json   curated site signatures
    views.py / serializers.py / urls.py
  drugintel/
    models.py        investigations, source authorization, evidence, triage, entities
    services.py      signed-update persistence, indicator extraction, correlations
    rules.py         deterministic, evidence-span-aware drug signal rules
    tasks.py         webhook handoff and approved-source scheduling
    views.py / serializers.py / urls.py
  jobs/ ai/ integrations/ sources/ reports/ config/
frontend/
  src/app/page.tsx           7-tab dashboard
  src/components/monitoring-panel.tsx  TanStack Query monitoring cockpit
  src/components/drug-intelligence-panel.tsx  source registry, triage, evidence, correlations
  src/components/app-providers.tsx     shared query cache + devtools
  src/hooks/use-monitoring-stream.ts   SSE invalidation + reconnect state
  src/app/layout.tsx         root providers + extension-error guard
  src/components/footprint-graph.tsx   Reagraph WebGL graph
  src/components/relay-map.tsx          MapLibre anomaly map
  src/lib/openapi/              generated SDK, types, and TanStack Query bindings
  src/lib/{api,types,query-keys,demo}.ts
infra/docker-compose.yml     PostgreSQL 18 extensions + Redis + Tor proxy
docs/openapi.yaml            generated API contract
.github/workflows/ci.yml     backend and frontend contract/build gates
```

---

_ToRsy — your buddy in the dark._ 🕶️
