# api.py
import os
import time
import json
import re
import asyncio
import threading
import logging
from typing import Optional
from urllib.parse import unquote

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from chain import (
    build_rag_chain,
    reindex_all,
    get_sources,                  # [{source, href?, preview?}, ...]
    rag_chain as eager_chain,     # may be None
    retriever as eager_retriever  # may be None
)

# ---------------- logging ----------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api")

def log_kv(**kw):
    logger.info(" ".join(f"{k}={v}" for k, v in kw.items()))

# --------------- FastAPI app -------------
app = FastAPI(title="RAG Chatbot")

# Serve local docs (only if directory exists)
DOCS_DIR = os.getenv("DOCS_DIR", "./docs")
if os.path.isdir(DOCS_DIR):
    app.mount("/docs", StaticFiles(directory=DOCS_DIR, html=False), name="docs")
else:
    logger.warning("Docs dir '%s' not found; /docs will not be mounted.", DOCS_DIR)

# CORS for Vite dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Globals populated on startup
rag_chain: Optional[object] = None
retriever: Optional[object] = None

# --------------- models ------------------
class ChatRequest(BaseModel):
    question: str

# ---------- output cleaners --------------
END_TOKENS_RE = re.compile(r"(?:</s>|<\|endoftext\|>|<\|im_end\|>)", re.IGNORECASE)
BANNER_RE = re.compile(r"welcome to .*?rag demo.*", re.IGNORECASE)

def clean_final(text: str) -> str:
    """For full (non-streaming) replies: strip end tokens & banner/noise lines."""
    text = END_TOKENS_RE.sub("", text or "")
    lines = []
    for line in (text.splitlines() if text else []):
        if BANNER_RE.search(line):
            continue
        if "langchain" in line.lower() and "chromadb" in line.lower():
            continue
        lines.append(line)
    return "\n".join(lines).strip()

def clean_stream_chunk(text: str) -> str:
    """For streaming tokens: remove end tokens only (DO NOT trim/normalize spacing)."""
    return END_TOKENS_RE.sub("", text or "")

def sse(data: str) -> str:
    return f"data: {data}\n\n"

# -------- lifecycle / readiness ----------
@app.on_event("startup")
def on_startup():
    """Prefer eager singletons from chain.py; otherwise build once."""
    global rag_chain, retriever
    app.state.rag_ready = False
    app.state.rag_error = None

    log_kv(event="startup", msg="initializing RAG")
    try:
        if eager_chain is not None and eager_retriever is not None:
            log_kv(event="startup", mode="eager_chain_and_retriever")
            rag_chain = eager_chain
            retriever = eager_retriever
        else:
            log_kv(event="startup", mode="build_chain_and_retriever")
            rag_chain, retriever = build_rag_chain()

        app.state.rag_ready = True
        log_kv(event="startup", status="ready")
    except Exception as e:
        app.state.rag_error = str(e)
        logger.exception("Failed to initialize RAG: %s", e)

# --------------- endpoints ---------------
@app.get("/health")
def health():
    return {
        "status": "ok" if getattr(app.state, "rag_ready", False) else "degraded",
        "docs_dir": DOCS_DIR,
        "chroma_dir": os.getenv("CHROMA_DIR", "./.chroma"),
        "embed_model": os.getenv("EMBED_MODEL", "BAAI/bge-small-en-v1.5"),
        "embed_device": os.getenv("EMBED_DEVICE", ""),
        "tgi_url": os.getenv("TGI_URL", "http://127.0.0.1:8080/"),
        "max_new_tokens": int(os.getenv("MAX_NEW_TOKENS", "192")),
        "error": getattr(app.state, "rag_error", None),
    }

@app.post("/reindex")
def reindex():
    """Delete the persisted Chroma DB and rebuild end-to-end."""
    global rag_chain, retriever
    try:
        t0 = time.perf_counter()
        rag_chain, retriever = reindex_all()
        dt = time.perf_counter() - t0
        log_kv(event="reindex", status="ok", seconds=f"{dt:.2f}")
        app.state.rag_ready = True
        app.state.rag_error = None
        return {"status": "ok", "message": "Reindex complete.", "seconds": round(dt, 2)}
    except Exception as e:
        app.state.rag_ready = False
        app.state.rag_error = str(e)
        logger.exception("Reindex failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Reindex failed: {e}")

@app.post("/chat")
async def chat(req: ChatRequest):
    """Non-streaming reply with citations."""
    if not getattr(app.state, "rag_ready", False) or rag_chain is None or retriever is None:
        raise HTTPException(status_code=503, detail="RAG not ready. Check /health and server logs.")

    q = (req.question or "").strip()
    if not q:
        raise HTTPException(status_code=400, detail="Missing question")

    log_kv(route="/chat", q=q)
    t0 = time.perf_counter()
    try:
        srcs = get_sources(q, retriever)
        first_token_time = None
        answer = ""

        # Generate (blocking iterator under the hood)
        for chunk in rag_chain.stream(q):
            if first_token_time is None:
                first_token_time = time.perf_counter()
            answer += chunk

        total = time.perf_counter() - t0
        ftt = None if first_token_time is None else (first_token_time - t0)
        log_kv(route="/chat", status="ok", total=f"{total:.2f}s", first_token=f"{(ftt or 0):.2f}s")

        return {
            "answer": clean_final(answer),
            "sources": srcs,
            "latency_sec": round(total, 2),
            "first_token_sec": None if ftt is None else round(ftt, 2),
        }
    except Exception as e:
        logger.exception("Chat failed: %s", e)
        return JSONResponse(
            status_code=500,
            content={"error": "Chat failed", "detail": str(e)},
        )

@app.get("/chat/stream")
async def chat_stream(request: Request, q: str):
    """
    SSE streaming: emits a 'sources' frame first, then progressive tokens,
    plus periodic keepalive pings. Uses minimal cleaning to preserve spaces.
    """
    if not getattr(app.state, "rag_ready", False) or rag_chain is None or retriever is None:
        raise HTTPException(status_code=503, detail="RAG not ready. Check /health and server logs.")

    question = unquote(q or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="Missing question")

    log_kv(route="/chat/stream", q=question)

    # compute sources once
    srcs = get_sources(question, retriever)

    async def event_gen():
        # initial frames
        yield sse(json.dumps({"type": "status", "message": "started"}))
        yield sse(json.dumps({"type": "sources", "items": srcs}))

        loop = asyncio.get_event_loop()
        queue: asyncio.Queue = asyncio.Queue()
        SENTINEL = object()
        first_token_time = None
        start_time = time.perf_counter()

        def producer():
            try:
                for chunk in rag_chain.stream(question):
                    text = chunk if isinstance(chunk, str) else str(chunk)
                    asyncio.run_coroutine_threadsafe(queue.put(text), loop)
            except Exception as e:
                asyncio.run_coroutine_threadsafe(queue.put(json.dumps({"__error__": str(e)})), loop)
            finally:
                asyncio.run_coroutine_threadsafe(queue.put(SENTINEL), loop)

        # run blocking generation in a thread
        threading.Thread(target=producer, daemon=True).start()

        # keepalive ping every 15s (helps proxies keep the connection open)
        async def keepalive():
            try:
                while True:
                    await asyncio.sleep(15)
                    await queue.put("__PING__")
            except asyncio.CancelledError:
                return

        ka_task = asyncio.create_task(keepalive())

        try:
            while True:
                # client disconnected?
                if await request.is_disconnected():
                    log_kv(route="/chat/stream", status="client_disconnected")
                    break

                item = await queue.get()
                if item is SENTINEL:
                    break

                # keepalive ping
                if item == "__PING__":
                    yield sse(": ping")
                    continue

                # producer error
                if isinstance(item, str) and item.startswith('{"__error__"'):
                    msg = json.loads(item).get("__error__", "Unknown error")
                    yield sse(json.dumps({"type": "error", "message": msg}))
                    break

                # normal token
                if first_token_time is None:
                    first_token_time = time.perf_counter()
                token = clean_stream_chunk(item if isinstance(item, str) else str(item))
                if token:
                    yield sse(json.dumps({"type": "token", "text": token}))
        finally:
            ka_task.cancel()
            total = time.perf_counter() - start_time
            ftt = None if first_token_time is None else (first_token_time - start_time)
            log_kv(route="/chat/stream", status="done", total=f"{total:.2f}s", first_token=f"{(ftt or 0):.2f}s")
            yield sse(json.dumps({"type": "done", "latency_sec": round(total, 2),
                                  "first_token_sec": None if ftt is None else round(ftt, 2)}))

    headers = {"Cache-Control": "no-cache", "Connection": "keep-alive"}
    return StreamingResponse(event_gen(), media_type="text/event-stream", headers=headers)
