import os
import logging
import re
import threading
import asyncio
import json
from typing import Optional
from urllib.parse import unquote

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from chain import (
    build_rag_chain,
    reindex_all,
    rag_chain as _rag_chain,  # optional eager build import
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api")

app = FastAPI(title="RAG Chatbot")

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


class ChatRequest(BaseModel):
    question: str


# ---------- cleaning helpers ----------
END_TOKENS_RE = re.compile(r"(?:</s>|<\|endoftext\|>|<\|im_end\|>)", re.IGNORECASE)
BANNER_RE = re.compile(r"welcome to .*?rag demo.*", re.IGNORECASE)

def clean_text(text: str) -> str:
    text = END_TOKENS_RE.sub("", text)
    lines = []
    for line in text.splitlines():
        if BANNER_RE.search(line):
            continue
        if "langchain" in line.lower() and "chromadb" in line.lower():
            continue
        lines.append(line)
    return "\n".join(lines).strip()


@app.on_event("startup")
def on_startup():
    global rag_chain, retriever
    app.state.rag_ready = False
    app.state.rag_error = None

    logger.info("🔧 Startup: building RAG chain...")
    try:
        if _rag_chain is not None:
            logger.info("Using eagerly built chain from chain.py")
            rag_chain = _rag_chain
        else:
            rag_chain, retriever = build_rag_chain()

        app.state.rag_ready = True
        logger.info("✅ RAG ready.")
    except Exception as e:
        app.state.rag_error = str(e)
        logger.exception("❌ Failed to build RAG chain on startup: %s", e)


@app.get("/health")
def health():
    return {
        "status": "ok" if getattr(app.state, "rag_ready", False) else "degraded",
        "docs_dir": os.getenv("DOCS_DIR", "./docs"),
        "chroma_dir": os.getenv("CHROMA_DIR", "./.chroma"),
        "embed_model": os.getenv("EMBED_MODEL", "BAAI/bge-large-en-v1.5"),
        "embed_device": os.getenv("EMBED_DEVICE", ""),
        "tgi_url": os.getenv("TGI_URL", "http://127.0.0.1:8080/"),
        "max_new_tokens": int(os.getenv("MAX_NEW_TOKENS", "512")),
        "error": getattr(app.state, "rag_error", None),
    }


@app.post("/reindex")
def reindex():
    global rag_chain, retriever
    try:
        rag_chain, retriever = reindex_all()
        app.state.rag_ready = True
        app.state.rag_error = None
        return {"status": "ok", "message": "Reindex complete."}
    except Exception as e:
        app.state.rag_ready = False
        app.state.rag_error = str(e)
        logger.exception("Reindex failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Reindex failed: {e}")


@app.post("/chat")
async def chat(req: ChatRequest):
    if not getattr(app.state, "rag_ready", False) or rag_chain is None:
        raise HTTPException(status_code=503, detail="RAG not ready. Check /health and server logs.")

    try:
        answer = ""
        for chunk in rag_chain.stream(req.question):
            answer += chunk
        answer = clean_text(answer)
        return {"answer": answer}
    except Exception as e:
        logger.exception("Chat failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Chat failed: {e}")


# -------- SSE Streaming --------

def _sse(data: str) -> str:
    return f"data: {data}\n\n"


@app.get("/chat/stream")
async def chat_stream(q: str):
    """
    Progressive SSE streaming endpoint.
    Connect with EventSource('/chat/stream?q=...').
    """
    if not getattr(app.state, "rag_ready", False) or rag_chain is None:
        raise HTTPException(status_code=503, detail="RAG not ready. Check /health and server logs.")

    question = unquote(q or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="Missing question")

    async def event_gen():
        # Initial status frame
        yield _sse(json.dumps({"type": "status", "message": "started"}))

        loop = asyncio.get_event_loop()
        queue: asyncio.Queue = asyncio.Queue()
        SENTINEL = object()

        def producer():
            try:
                for chunk in rag_chain.stream(question):
                    text = chunk if isinstance(chunk, str) else str(chunk)
                    asyncio.run_coroutine_threadsafe(queue.put(text), loop)
            except Exception as e:
                asyncio.run_coroutine_threadsafe(queue.put(json.dumps({"__error__": str(e)})), loop)
            finally:
                asyncio.run_coroutine_threadsafe(queue.put(SENTINEL), loop)

        thread = threading.Thread(target=producer, daemon=True)
        thread.start()

        try:
            while True:
                item = await queue.get()
                if item is SENTINEL:
                    break

                if isinstance(item, str) and item.startswith('{"__error__"'):
                    msg = json.loads(item).get("__error__", "Unknown error")
                    yield _sse(json.dumps({"type": "error", "message": msg}))
                    break

                text = clean_text(item if isinstance(item, str) else str(item))
                if text:
                    yield _sse(json.dumps({"type": "token", "text": text}))
        finally:
            yield _sse(json.dumps({"type": "done"}))

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        # "X-Accel-Buffering": "no",  # uncomment if behind nginx
    }
    return StreamingResponse(event_gen(), media_type="text/event-stream", headers=headers)
