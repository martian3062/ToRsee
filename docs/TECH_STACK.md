# ToRsy Technical Stack

## Architecture

ToRsy is a monorepo with a Django API backend, a Next.js dashboard, and local Docker Compose infrastructure.

- `backend/`: Django 5.2 LTS, Django REST Framework, Celery, Redis, pytest.
- `frontend/`: Next.js App Router, TypeScript, Tailwind CSS, lucide-react icons.
- `infra/`: local Postgres and Redis.
- `scripts/use-e-cache.ps1`: pins Python venv, package caches, and model caches to `E:\cache\ToRsy`.

The backend defaults to `PROVIDER_MOCK_MODE=true`, so the whole pipeline works without spending paid API credits.

## Runtime Flow

1. The dashboard posts URLs to `POST /api/jobs/ingest`.
2. Django creates an ingestion job and job targets.
3. Celery runs the job. In local mode, Celery is eager and executes in-process.
4. The fetch chain tries Firecrawl, ZenRows, Bright Data, TinyFish, then direct HTTP according to provider preference.
5. Content is stored as a `Document`; Groq creates a summary; Hugging Face-style embeddings are generated.
6. Pinecone receives vectors when configured; otherwise local search is used.
7. Telegram sends a job-complete message when configured; otherwise a mock send result is recorded.

## API Surface

- `GET /api/health`: database, Redis, and provider readiness.
- `GET /api/jobs/`: latest ingestion jobs with targets and documents.
- `GET /api/jobs/{id}`: one job with target details.
- `POST /api/jobs/ingest`: body `{ urls, provider_preference, tags, notify }`.
- `POST /api/search`: body `{ query, top_k }`; returns Pinecone matches and local document matches.
- `POST /api/ai/summarize`: body `{ text }` or `{ document_ids }`.
- `POST /api/telegram/webhook`: Telegram Bot API update payload.

## Provider Roles

- Firecrawl: primary clean markdown fetch.
- ZenRows: anti-bot fallback.
- Bright Data: structured scraper APIs and collector-based data.
- TinyFish: natural-language web agent/browser automation.
- Groq: fast chat, summaries, extraction, and JSON reasoning.
- Hugging Face: embeddings and optional model routing.
- Pinecone: semantic vector index.
- Supabase: hosted Postgres-compatible database and optional storage.
- Sarvam: Indian-language speech, translation, and TTS.
- TabPFN: small tabular classification/regression.
- Pexels: image/video media search for content workflows.
- Telegram: alerts and commands: `/status`, `/search <query>`, `/summarize <query>`.
- Stitch: design exploration and UI handoff placeholder.

## Environment

Copy `.env.example` to `.env`, then set keys only for the providers you want live. Keep `PROVIDER_MOCK_MODE=true` for demos.

Important local defaults:

- `DATABASE_URL=postgres://torsy:torsy@127.0.0.1:5432/torsy`
- `REDIS_URL=redis://127.0.0.1:6379/0`
- `CELERY_TASK_ALWAYS_EAGER=true`
- `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api`

Cache and environment setup:

```powershell
.\scripts\use-e-cache.ps1
```

This sets:

- `UV_PROJECT_ENVIRONMENT=E:\cache\ToRsy\.venv`
- `UV_CACHE_DIR=E:\cache\ToRsy\uv`
- `UV_PYTHON_INSTALL_DIR=E:\cache\ToRsy\python`
- `PIP_CACHE_DIR=E:\cache\ToRsy\pip`
- `NPM_CONFIG_CACHE=E:\cache\ToRsy\npm`
- `HF_HOME=E:\cache\ToRsy\hf`
- `TORCH_HOME=E:\cache\ToRsy\torch`
- `TRANSFORMERS_CACHE=E:\cache\ToRsy\transformers`

## Local Runbook

```powershell
Copy-Item .env.example .env
.\scripts\use-e-cache.ps1
docker compose -f infra/docker-compose.yml up -d
cd backend
uv sync --dev
uv run python manage.py migrate
uv run python manage.py runserver 127.0.0.1:8000
```

```powershell
.\scripts\use-e-cache.ps1
cd frontend
npm install
npm run dev
```

For no-Docker smoke tests, leave `DATABASE_URL` unset and Django falls back to local SQLite.

If `8000` is already occupied, run Django on another port such as `8025` and set
`NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8025/api` before starting Next.

## Verification

```powershell
.\scripts\use-e-cache.ps1
cd backend
uv run pytest
cd ..\frontend
npm run build
```

The first verification pass should show provider statuses as `mocked` unless keys are present.
