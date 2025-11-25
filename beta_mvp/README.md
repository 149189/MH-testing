# Agentic Multilingual News Verification API

This project is a skeleton for an agentic, multilingual news verification pipeline.
It uses FastAPI, Celery, PostgreSQL, Redis, and FAISS, and exposes an HTTP API
for asynchronous verification and reviewer workflows.

## Components

- **FastAPI** backend (`main.py`, `api/routes/*`)
- **Celery** worker (`tasks.py`, `celery_app.py`)
- **PostgreSQL** for structured data (`db/models.py`)
- **Redis** for Celery broker/result backend and caching (`celery_app.py`, `utils/cache_manager.py`)
- **FAISS** placeholder for vector retrieval (`rag/retriever.py`)
- **LLM-based agents** for claims, stance, and veracity (`agents/`, `models/`)
- **Metrics & analytics** (`monitoring/metrics.py`, `/api/analytics`)

## Setup

1. Create and activate a virtualenv, then install dependencies:

```bash
cd beta_mvp
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
```

2. Configure environment variables (examples):

```bash
export DATABASE_URL="postgresql+psycopg2://user:password@localhost:5432/news_verification"
export REDIS_URL="redis://localhost:6379/0"
export CELERY_BROKER_URL="$REDIS_URL"
export CELERY_RESULT_BACKEND="redis://localhost:6379/1"
export GEMINI_API_KEY="your-gemini-key"   # optional for LLM steps
export GEMINI_MODEL="gemini-1.5-flash"    # or another compatible model
export DISCORD_BOT_TOKEN="..."         # optional
export TELEGRAM_BOT_TOKEN="..."        # optional
```

3. Ensure PostgreSQL and Redis are running and accessible with the URLs above.

## Running the stack

### FastAPI app

```bash
cd beta_mvp
uvicorn main:app --reload --port 8000
```

Visit `http://localhost:8000/docs` for interactive API documentation.

### Celery worker

In another terminal with the same virtualenv and env vars:

```bash
cd beta_mvp
celery -A celery_app.celery_app worker -l info
```

## Key endpoints

- `POST /api/verify` – enqueue a verification job, returns `task_id`.
- `GET /api/verify/{task_id}` – fetch verification results (claims, evidence, stances, veracity).
- `GET /api/claims/pending_review` – list claims awaiting human review.
- `POST /api/claims/{id}/decision` – submit reviewer decision, overriding AI verdict.
- `GET /api/analytics` – basic metrics dashboard (avg time, language mix, TP/FP counts).

## Notes

- The RAG and retrieval components are stubs; plug in real FAISS indices and web/search backends.
- Speech-to-text, rich categorization, and production-grade metrics should be added before
  using this in a live system.
