# Semantic Code Search

Semantic search over source code. Index a repository, then search by meaning, generate AI explanations, trace call chains, and visualise dependency graphs.

Built as a single-worker FastAPI service — an architecture that makes event-loop blocking immediately visible, and therefore worth measuring hard. The result: **13 defects fixed, a 13-minute outage eliminated, 7.1x throughput and 410x better p99 latency under load.**

Full performance report: **[perf/RESULTS.md](perf/RESULTS.md)** · Detailed defect log: **[perf/PERF-LOG.txt](perf/PERF-LOG.txt)**

---

## Table of Contents

- [How It Works](#how-it-works)
- [Features](#features)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Performance](#performance)
- [Architecture](#architecture)
- [API Reference](#api-reference)
- [Project Structure](#project-structure)
- [Testing](#testing)
- [Load Testing](#load-testing)
- [Key Decisions](#key-decisions)
- [License](#license)

---

## How It Works

1. Point the tool at a local repository path.
2. The backend scans and parses source files with **tree-sitter**, extracting symbols (functions, classes, methods).
3. Each symbol is embedded by a vector model and stored in **Qdrant**, tagged with its repository.
4. At query time your natural-language query is embedded and matched against the vector store, filtered to that repository.
5. Retrieved context is passed to an LLM for explanation and trace tasks.

```
Browser ──► React SPA ──► FastAPI ──► PostgreSQL   (symbols, edges, metadata)
                              ├────► Qdrant       (768-dim vectors)
                              ├────► Ollama/LLM   (embeddings, explanations)
                              └────► Ollama/LLM   (call-graph reasoning)
```

---

## Features

**Search.** Query in natural language — "where is authentication handled". Returns symbols ranked by semantic similarity with file paths and line numbers.

**Explain.** Retrieves relevant code and asks the LLM for a structured explanation with source references.

**Trace.** Follows calls and imports from the initial results to map execution paths.

**Graph.** Interactive symbol-relationship visualisation (imports, calls, defines, inherits), paginated so large repositories stay responsive.

**Multi-repository.** Index many repositories side by side. Vector collections are shared, but every read and delete is repository-scoped — indexing or deleting one repository never touches another's data.

---

## Quick Start

### Docker (recommended)

```bash
git clone <repo-url> && cd Semantic-Code-Search
cp .env.docker .env
# Edit .env if you need a specific host folder mounted for indexing
docker compose --profile full up -d
```

Frontend: <http://localhost> · API: <http://localhost:8000>

To index a repository, the backend needs that folder mounted into the container:

```yaml
# docker-compose.yml
volumes:
  - "${HOST_USER_DIR:-C:/Users/}:${HOST_MOUNT_PATH:-/host/users}"
```

```env
# .env — point the mount at the code you want to index
HOST_USER_DIR=D:/Code/Projects
HOST_MOUNT_PATH=/host/projects
```

### Local development

```bash
# Backend
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
pnpm install
pnpm dev
```

Frontend: <http://localhost:5173>

**Requirements:** Python 3.11+, Node.js 18+, PostgreSQL 14+, Qdrant, and either an LLM API key or [Ollama](https://ollama.com) running locally.

> **Docker note:** `backend/models.json` seeds the active provider and is intentionally **not** excluded by `.dockerignore`. If it is missing, the backend silently falls back to `EMBEDDING_PROVIDER` (gemini by default) and every search fails with a 403 if no API key is set.

---

## Configuration

### Required

```env
DATABASE_URL=postgresql+asyncpg://user:pass@host/dbname
QDRANT_URL=http://qdrant:6333
QDRANT_API_KEY=
```

### Providers

Providers are configured through the UI (Settings in the sidebar) and persisted to `backend/models.json`.

| Provider | LLM | Embeddings | Notes |
|----------|-----|------------|-------|
| Gemini | gemini-2.5-flash | gemini-embedding-001 | Free tier available |
| OpenAI | gpt-4o-mini | text-embedding-3-small | Pay per token |
| Anthropic | claude-sonnet-4 | — | LLM only |
| Ollama | Any local model | nomic-embed-text | Free, fully local |
| Custom | Any | Any | OpenAI-compatible endpoints |

Env defaults (used when no model is configured):

```env
EMBEDDING_PROVIDER=gemini
LLM_PROVIDER=gemini
GEMINI_API_KEY=
OLLAMA_URL=http://localhost:11434
```

### Connection pool

```env
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=1800
```

SQLAlchemy's default (5 + 10) silently caps concurrency at 15 connections, which surfaces as unexplained queueing latency rather than an error.

---

## Performance

Measured with k6 against the Docker Compose stack on 4 cores / 8 threads / 16 GB, single Uvicorn worker. Full methodology in [perf/RESULTS.md](perf/RESULTS.md).

### Background indexing under live traffic

The critical test: continuous foreground traffic while a full repository re-index runs.

| Metric | Before | After | Change |
|---|---|---|---|
| Requests served | 1,346 | **8,901** | **6.6x** |
| Throughput | 5.25 req/s | **37.03 req/s** | **7.1x** |
| Mean latency | 498.6 ms | **9.4 ms** | **53x** |
| p95 latency | 143.9 ms | **27.4 ms** | **5.3x** |
| p99 latency | 29,994 ms | **73.1 ms** | **410x** |
| Worst case | 29,998 ms | **991.5 ms** | **30x** |
| Blocked requests | **21** | **0** | eliminated |
| Error rate | 1.56 % | **0 %** | eliminated |

### All suites

| Suite | Metric | Before | After |
|---|---|---|---|
| Search load | Throughput | 8.26 req/s | **20.60 req/s** |
| Search load | p95 | 3,762.6 ms | **1,380.5 ms** |
| Read load | Throughput | 60.16 req/s | **104.90 req/s** |
| Read load | p95 | 1,672.6 ms | **767.8 ms** |
| Spike (60 VU) | Throughput | 7.56 req/s | **18.32 req/s** |
| Spike (60 VU) | p95 | 10,336.9 ms | **3,838.5 ms** |
| Soak (10 min) | Throughput | 7.87 req/s | **15.34 req/s** |
| Soak (10 min) | p95 | 2,306.3 ms | **600.4 ms** |

Zero request failures in every suite after remediation. Soak latency drift **1.63x** against a 2.0x gate — **PASS**.

### What made the difference

| Fix | Impact |
|---|---|
| `os.walk` with in-place pruning instead of `Path.rglob("*")` | 705,000 directory entries → ~1,300; **12 min → 0.04 s** |
| Scanner + parsing offloaded to a thread pool | Outage eliminated |
| Synchronous → `AsyncQdrantClient` | Request path no longer blocks the loop |
| Batched embedding requests | Indexing **~12 min → ~12 s** |
| Batched node hydration (removed N+1) | ~10 fewer round-trips per search |
| Explicit pool sizing | Removed hidden 15-connection ceiling |
| Repository-scoped vector deletes | Fixed cross-repository data loss |

**Key finding:** baseline p95 was 143.9 ms — a clear **PASS** against a 5,000 ms threshold — while the server was dead for 13 minutes. Percentiles cannot detect an outage, so the suite now gates on absolute availability counters (`blocked_requests == 0`).

---

## Architecture

```
frontend (React + Vite + Zustand)
    │  /api proxy
    ▼
backend (FastAPI, single Uvicorn worker)
    ├── api/           route handlers
    ├── core/          scanner, tree-sitter parser, relationship extraction
    ├── embedding/     embedding providers + Qdrant vector store
    ├── llm/           LLM providers
    ├── repositories/  SQLAlchemy data access
    ├── services/      indexing, search, explain, trace
    ├── database.py    async engine + tuned connection pool
    └── model_store.py JSON-backed model configuration

postgres (symbols, edges)     qdrant (vectors, payload-filtered by repository_id)
```

**Single-worker by design.** All blocking work — filesystem traversal, parsing, vector-store I/O — runs in threads or through async clients. This is the invariant the performance work exists to protect, and the reason regressions are caught by tests rather than by users.

---

## API Reference

All endpoints are prefixed with `/api`.

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/repositories/index` | Index a repository by path |
| `GET` | `/repositories` | List indexed repositories |
| `DELETE` | `/repositories/{id}` | Delete a repository and its vectors |
| `GET` | `/repositories/browse?path=` | List subdirectories for the file browser |
| `GET` | `/repositories/{id}/status` | Indexing progress |
| `POST` | `/search` | Semantic search |
| `POST` | `/explain` | LLM explanation of code |
| `POST` | `/trace` | Trace code flow with neighbours |
| `GET` | `/graph/{repo_id}` | Knowledge graph — supports `limit` and `symbol_type` |
| `GET` | `/symbols/{id}` | Symbol detail |
| `GET` | `/symbols/{id}/relationships` | Symbol relationships |
| `GET` `POST` | `/models` | List / create model configs |
| `PUT` `DELETE` | `/models/{id}` | Update / delete a model config |
| `POST` | `/models/{id}/activate` | Set as active model |
| `GET` | `/models/{id}/health` | Provider connectivity check |
| `GET` `PUT` | `/config/providers` | Read / switch the active provider |

---

## Project Structure

```
backend/
  app/
    api/            route handlers
    core/           scanner, parser, relationship extraction
    embedding/      embedding providers + Qdrant vector store
    llm/            LLM providers
    models/         SQLAlchemy models + enums
    repositories/   data access layer
    schemas/        Pydantic request/response models
    services/       indexing, search, explain, trace
    config.py       settings + runtime provider overrides
    database.py     async engine + connection pool
    model_store.py  model configuration persistence
  tests/            95-test regression suite
  alembic/          migrations

frontend/
  src/
    components/     React components
    services/       API client
    schemas.ts      Zod schemas + TypeScript types
    store.ts        Zustand state

perf/               k6 load-testing suite
  k6/               test scripts
  results/          captured summaries (raw samples gitignored)
  run-k6.ps1        harness
```

---

## Testing

```bash
# Backend
cd backend
uv sync --group dev
pytest -q                 # 95 passed, 2 skipped
ruff check .              # All checks passed!

# Frontend
cd frontend
pnpm test
pnpm exec tsc --noEmit
```

The backend suite covers scanning and pruning, tree-sitter parsing, relationship extraction, the model store, provider-resolution consistency, the Qdrant client contract, vector-store collection reuse, and graph edge scoping. It runs entirely offline.

Tests added during the performance work were **mutation-tested** — each was verified to fail when its corresponding fix is reverted, so they guard real invariants rather than current behaviour.

---

## Load Testing

```bash
cd perf

./run-k6.ps1 -Script /scripts/smoke.js           -Name smoke      # always first
./run-k6.ps1 -Script /scripts/probe.js           -Name probe      # verify target app
./run-k6.ps1 -Script /scripts/read-load.js       -Name read
./run-k6.ps1 -Script /scripts/search-load.js     -Name search
./run-k6.ps1 -Script /scripts/index-contention.js -Name contention -Env @{ RESET_REPO='true' }
./run-k6.ps1 -Script /scripts/spike.js           -Name spike -Env @{ DURATION='60s' }
./run-k6.ps1 -Script /scripts/soak.js            -Name soak  -Env @{ DURATION='10m' }
```

- Raw samples are opt-in (`-Raw`); they run to ~100 MB per run.
- Results land in `perf/results/<name>-summary.json` and `<name>-stdout.txt`.
- `run-k6.ps1` surfaces k6 stderr and **fails the run on script errors even when k6 exits 0** — a script exception produces no requests, so thresholds would otherwise stay green while the test is broken.
- `probe.js` verifies the target application by its OpenAPI title and **exits non-zero on mismatch**, because load tests once ran against the wrong application on a shadowed port without failing.
- Benchmarks always run against `BASE_URL=http://backend:8000` (the compose network), so a host port conflict cannot silently redirect a measurement. Note that if another local service occupies host port 8000, browse to the container service rather than `localhost`.

---

## Key Decisions

- **tree-sitter 0.21.3** pinned — newer versions break the `tree-sitter-languages` wrapper.
- **`os.walk` with in-place pruning** instead of `Path.rglob("*")`, which cannot prune and walked ~705,000 directory entries to find ~1,300 files.
- **All blocking work off the event loop** — threads for CPU/IO, `AsyncQdrantClient` for Qdrant. The core invariant of this service.
- **Qdrant `query_points()`** replaces the deprecated `search()` API; client pinned `>=1.12.0,<1.13.0` to match the server.
- **Shared collection, repository-scoped payloads.** One collection for all repositories, every read and delete filtered by `repository_id`. Recreating the collection on re-index destroyed every other repository's data (BUG-012).
- **Async SQLAlchemy throughout**, with an explicitly sized connection pool.
- **JSON model store** (`models.json`) rather than a database table — simple, no migration, easy to version.
- **Pagination by default** on the graph endpoint, with edges scoped to the returned node page so the client never receives dangling references.

---

## License

MIT — see [LICENSE](LICENSE).