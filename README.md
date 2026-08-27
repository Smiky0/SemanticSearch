# Semantic Code Search

Semantic search over source code. Index a repository, then search by meaning, get AI explanations, trace call chains, and visualize dependency graphs.

## How It Works

1. Point the tool at a local repository path
2. Backend parses source files with tree-sitter, extracts symbols (functions, classes, methods)
3. Symbols are embedded via a vector model and stored in Qdrant
4. At query time, your natural language query is embedded and matched against the vector store
5. Retrieved context is passed to an LLM for explanation/trace tasks

```
Browser ──> React SPA ──> FastAPI ──> PostgreSQL (metadata)
                                    ──> Qdrant (vectors)
                                    ──> LLM API (explanations)
```

## Requirements

- Python 3.11+
- Node.js 18+
- PostgreSQL 14+ (or Neon/Aiven serverless)
- Qdrant (self-hosted or cloud)
- An LLM API key (Gemini, OpenAI, Claude) or Ollama running locally

## Setup

```bash
git clone <repo-url> && cd Semantic-Code-Search

# Backend
cd backend
cp ../.env.example .env
# Edit .env with your database, Qdrant, and API credentials
uv sync

# Frontend
cd ../frontend
pnpm install
```

### Environment Variables

Required in `backend/.env`:

```env
DATABASE_URL=postgresql+asyncpg://user:pass@host/dbname?sslmode=require
QDRANT_URL=https://your-cluster.qdrant.io:6333
QDRANT_API_KEY=your-qdrant-api-key
```

LLM/embedding providers are configured through the UI (Settings gear icon in sidebar). Defaults can be set via env vars:

```env
GEMINI_API_KEY=your-key
OPENAI_API_KEY=your-key
OLLAMA_URL=http://localhost:11434
```

### Running

```bash
# Terminal 1 — backend
cd backend
uv run uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend
pnpm dev
```

Open http://localhost:5173

### Docker

Two modes — all-in-one or external services:

```bash
# Full stack (Postgres + Qdrant + app in Docker)
cp .env.docker .env
docker compose --profile full up -d

# External services (your own Postgres + Qdrant)
# Set DATABASE_URL, QDRANT_URL, QDRANT_API_KEY in .env
docker compose up -d backend frontend
```

Frontend serves at http://localhost:80 (nginx), proxies `/api` to backend.

### Environment

## What It Does

**Search.** Type a natural language query like "where is authentication handled". Returns matching symbols ranked by semantic similarity with file paths and line numbers.

**Explain.** Toggle AI mode and ask a question. Retrieves relevant code, passes it to the LLM, and returns a structured explanation with source references.

**Trace.** Follows function calls and imports from the initial search results to map execution paths.

**Graph.** Interactive visualization of the codebase's symbol relationships (imports, calls, defines, inherits).

## Provider Support

| Provider | LLM | Embeddings | Notes |
|----------|-----|------------|-------|
| Gemini | gemini-2.5-flash | gemini-embedding-001 | Free tier available |
| OpenAI | gpt-4o-mini | text-embedding-3-small | Pay per token |
| Anthropic | claude-sonnet-4-20250514 | — | LLM only; pair with another for embeddings |
| Ollama | Any local model | nomic-embed-text | Free, runs on your machine |
| Custom | Any | Any | OpenAI-compatible `/v1/chat/completions` and `/v1/embeddings` |

Providers are managed through the UI. You can add, edit, delete, and switch between models at runtime.

## API Reference

All endpoints are prefixed with `/api`.

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/repositories/index` | Index a repository by path |
| `GET` | `/repositories` | List indexed repositories |
| `DELETE` | `/repositories/{id}` | Delete a repository and its vectors |
| `GET` | `/repositories/browse?path=` | List subdirectories for the file browser |
| `POST` | `/search` | Semantic search |
| `POST` | `/explain` | LLM explanation of code |
| `POST` | `/trace` | Trace code flow with neighbors |
| `GET` | `/graph/{repo_id}` | Knowledge graph data |
| `GET` | `/models` | List configured models |
| `POST` | `/models` | Create a model config |
| `PUT` | `/models/{id}` | Update a model config |
| `DELETE` | `/models/{id}` | Delete a model config |
| `POST` | `/models/{id}/activate` | Set as active model |
| `GET` | `/models/{id}/health` | Check provider connectivity |

## Project Structure

```
backend/
  app/
    api/            # Route handlers
    core/           # Scanner, parser, relationship extraction
    embedding/      # Embedding providers + Qdrant vector store
    llm/            # LLM providers
    models/         # SQLAlchemy models + enums
    repositories/   # Database access layer
    schemas/        # Pydantic request/response models
    services/       # Business logic (indexing, search, explain, trace)
    config.py       # Settings + runtime provider overrides
    main.py         # FastAPI app, lifespan, exception handlers
    model_store.py  # JSON-based model configuration persistence
  alembic/          # Database migrations

frontend/
  src/
    components/     # React components
    services/       # API client
    schemas.ts      # Zod schemas + TypeScript types
    store.ts        # Zustand state management
    index.css       # Theme variables + code highlighting
```

## Development

```bash
# Lint backend
cd backend && uv run ruff check .

# Typecheck frontend
cd frontend && pnpm exec tsc --noEmit

# Database migrations
cd backend
uv run alembic revision --autogenerate -m "description"
uv run alembic upgrade head
```

## Key Decisions

- **tree-sitter 0.21.3** pinned for compatibility with tree-sitter-languages. Newer versions break the wrapper.
- **Qdrant `query_points()`** replaces deprecated `search()` API.
- **Async SQLAlchemy** throughout. Neon requires `ssl=require` in connect_args.
- **JSON model store** (`models.json`) instead of database table for model configs — simpler, no migration needed, easy to version control.
- **Runtime provider switching** via module-level variables, not env var reload. Allows switching without restart.

## License

MIT
