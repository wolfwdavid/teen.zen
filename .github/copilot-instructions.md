<!-- .github/copilot-instructions.md - guidance for AI coding agents working on this repo -->
# Quick context
This repository contains a mobile/web app and a small RAG (Retrieval-Augmented Generation) demo
under `chatbot-rag/`. The RAG demo is split into two main parts:

- Frontend: `chatbot-rag/frontend` — Vite + React app that opens an SSE stream to the backend.
- Backend: `chatbot-rag/backend` — FastAPI service that builds a LangChain + Chroma index and
  streams generation tokens from a text-generation endpoint (TGI/HF TGI).

Work here usually involves debugging the RAG pipeline (`chain.py`), the FastAPI endpoints
(`api.py`), or the front-end streaming UI (`frontend/src/components/ChatBoxStream.jsx`).

## Architecture (concise)
- `chain.py` builds embeddings -> Chroma vectorstore -> retriever -> HuggingFaceEndpoint (TGI).
  - `build_rag_chain()` returns a `rag_chain` object that supports `.stream(question)`.
  - Documents are read from `DOCS_DIR` (default `./docs`), split, embedded, and persisted to `CHROMA_DIR`.
- `api.py` exposes:
  - `GET /health` — simple diagnostics (shows env defaults like `TGI_URL`, `EMBED_MODEL`).
  - `POST /reindex` — delete the persisted Chroma DB and rebuild from `DOCS_DIR`.
  - `POST /chat` — non-streaming chat that concatenates `.stream()` chunks and returns final answer.
  - `GET /chat/stream?q=...` — Server-Sent Events (SSE) streaming API. Messages are JSON with `type` values: `status`, `sources`, `token`, `error`, `done`.
- Frontend (`ChatBoxStream.jsx`) uses SSE to `/chat/stream` and expects `token` frames to append text.

## Key environment variables (discoverable defaults in `chain.py` / `api.py`)
- `TGI_URL` (default `http://127.0.0.1:8080/`) — text-generation inference endpoint used by `HuggingFaceEndpoint`.
- `DOCS_DIR` (default `./docs`) — directory scanned for `.txt` and `.md` sources.
- `CHROMA_DIR` (default `./.chroma`) — persistent Chroma DB.
- `EMBED_MODEL` (default `BAAI/bge-small-en-v1.5`) — embedding model used by `HuggingFaceEmbeddings`.
- `EMBED_DEVICE` — prefer `cpu` or `cuda` or leave empty for auto.
- `EAGER_BUILD` — when true, `chain.py` will build the chain at import time (used for faster startup under some conditions).
- Generation tuning: `MAX_NEW_TOKENS`, `TEMPERATURE`, `REPETITION_PENALTY`, `CHUNK_SIZE`, `CHUNK_OVERLAP`.

## Developer workflows & commands
1) Start the inference (TGI) service (recommended: GPU host; compose included under `chatbot-rag/backend`):

```bash
cd chatbot-rag/backend
docker compose up -d
# or: docker compose up --build
```

2) Run backend FastAPI (in `chatbot-rag/backend`):

```bash
python -m venv .venv
source .venv/Scripts/activate   # on Bash/WSL/Unix-like (Windows PowerShell: .venv\\Scripts\\Activate.ps1)
pip install -r requirements.txt
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

3) Run frontend dev server (in `chatbot-rag/frontend`):

```bash
cd chatbot-rag/frontend
npm install
npm run dev
# open http://localhost:5173
```

4) Debugging quick checks:
- Curl health: `curl -sS http://10.20.50.249:8000/health`
- Trigger reindex: `curl -X POSThttp://10.20.50.249:8000/reindex`
- POST chat (non-streaming): `curl -X POST -H 'Content-Type: application/json' -d '{"question":"hi"}' http://10.20.50.249:8000/chat`

## Project-specific patterns & conventions
- SSE streaming contract: backend sends JSON lines via SSE with these `type` keys:
  - `status` (startup), `sources` (list of citation dicts), `token` (piece of generated text), `error`, `done`.
  - Frontend expects `token` frames to append text incrementally — preserve whitespace in streamed chunks.
- Text cleanups: `api.py` exposes `clean_stream_chunk()` (for streaming tokens — do NOT strip whitespace) and `clean_final()` (for final responses).
- Citation metadata: `chain._load_documents()` ensures each `Document` has a `source` metadata field; `get_sources()` returns `{source, href?, preview?}` where `href` points to `/docs/...` if `DOCS_DIR` is mounted.
- Reindexing: `POST /reindex` deletes `CHROMA_DIR` and rebuilds from `DOCS_DIR`. Use this when source content changes.
- Eager vs lazy build: default is to build RAG on startup; set `EAGER_BUILD=true` to build at import time (useful in some Docker/container setups).

## Files to inspect for common tasks
- `chatbot-rag/backend/chain.py` — embedding, vectorstore, retriever, prompt template, `.stream()` chain construction.
- `chatbot-rag/backend/api.py` — endpoints, SSE implementation, token cleaning, startup lifecycle.
- `chatbot-rag/backend/requirements.txt` — minimal Python deps for the backend.
- `chatbot-rag/backend/docker-compose.yml` — example TGI service configuration (HF TGI image).
- `chatbot-rag/frontend/src/components/ChatBoxStream.jsx` — SSE client logic and UI expectations.
- `chatbot-rag/frontend/package.json` — dev scripts (Vite). Dev server exposes port 5173 by default (CORS allowed in `api.py`).

## Integration notes & gotchas (from code)
- TGI must be reachable at `TGI_URL` (default port 8080). If TGI is not running, startup will fail or streaming will error.
- The Chroma vectorstore is persisted under `CHROMA_DIR`; when debugging, removing that directory forces a rebuild and can surface issues with document parsing or embeddings.
- `chain.py` currently uses `HuggingFaceEndpoint` streaming; the chain object is assembled using `RunnablePassthrough | PromptTemplate | llm` and exposes `.stream(question)` used in `api.py`.
- `DOCS_DIR` contents are expected to be plaintext (`.txt`) or Markdown (`.md`). If no docs are present a build will raise an error — add sample docs to `chatbot-rag/backend/docs` for local testing.

## Testing
- There is a placeholder `chatbot-rag/backend/test_api.py` — not a complete test suite. Use `uvicorn` logs and `/health` for quick checks.

## If you change code that affects streaming, vectorstore, or docs
- Update `chain.py` and `api.py` together; ensure the SSE contract keys (`type`) remain compatible with `ChatBoxStream.jsx`.
- If you change how `Document.metadata.source` is set, update `get_sources()` to preserve `href` creation.

---
If any section needs more detail (example env files, a minimal test harness, or known local troubleshooting steps), tell me which area to expand and I will iterate.
