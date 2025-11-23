# api_v2.py
import os
import logging
import threading
import asyncio
import json
from typing import Optional
from urllib.parse import unquote

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from chain_v2 import (
    build_rag_chain,
    reindex_all,
    get_sources,
    rag_chain as eager_chain,
    retriever as eager_retriever,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api_v2")

app = FastAPI(title="RAG Chatbot – V2 (ONNX)")

DOCS_DIR = os.getenv("DOCS_DIR", "./docs")
if os.path.isdir(DOCS_DIR):
    app.mount("/docs", StaticFiles(directory=DOCS_DIR, html=False), name="docs")
else:
    logger.warning("Docs dir '%s' not found; /docs will not be mounted.", DOCS_DIR)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

rag_chain: Optional[object] = None
retriever: Optional[object] = None


class ChatRequest(BaseModel):
    question: str


@app.on_event("startup")
def on_startup():
    global rag_chain, retriever
    app.state.rag_ready = False
    app.state.rag_error = None

    logger.info("🔧 Startup (V2): initializing RAG + ONNX...")
    try:
        if eager_chain is not None and eager_retriever is not None:
            logger.info("Using eager rag_chain + retriever from chain_v2")
            rag_chain = eager_chain
            retriever = eager_retriever
        else:
            logger.info("Building chain + retriever...")
            rag_chain, retriever = build_rag_chain()

        app.state.rag_ready = True
        logger.info("✅ RAG V2 ready.")
    except Exception as e:
        app.state.rag_error = str(e)
        logger.exception("❌ Failed to initialize RAG V2: %s", e)


@app.get("/health")
def health():
    return {
        "status": "ok" if getattr(app.state, "rag_ready", False) else "degraded",
        "docs_dir": DOCS_DIR,
        "chroma_dir": os.getenv("CHROMA_DIR", "./.chroma"),
        "embed_model": os.getenv("EMBED_MODEL", "BAAI/bge-small-en-v1.5"),
        "embed_device": os.getenv("EMBED_DEVICE", ""),
        "onnx_model_dir": os.getenv("LOCAL_ONNX_MODEL_DIR", "./models/local-onnx-model"),
        "max_new_tokens": int(os.getenv("MAX_NEW_TOKENS", "120")),
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
    if not getattr(app.state, "rag_ready", False) or rag_chain is None or retriever is None:
        raise HTTPException(status_code=503, detail="RAG V2 not ready. Check /health and logs.")
    try:
        srcs = get_sources(req.question, retriever)
        answer = rag_chain.invoke(req.question)  # type: ignore[union-attr]
        return {"answer": answer, "sources": srcs}
    except Exception as e:
        logger.exception("Chat failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Chat failed: {e}")


def _sse(data: str) -> str:
    return f"data: {data}\n\n"


@app.get("/chat/stream")
async def chat_stream(q: str):
    if not getattr(app.state, "rag_ready", False) or rag_chain is None or retriever is None:
        raise HTTPException(status_code=503, detail="RAG V2 not ready. Check /health and logs.")

    question = unquote(q or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="Missing question")

    logger.info("💬 /chat/stream (V2) question=%r", question)
    srcs = get_sources(question, retriever)

    async def event_gen():
        yield _sse(json.dumps({"type": "status", "message": "started"}))
        yield _sse(json.dumps({"type": "sources", "items": srcs}))

        loop = asyncio.get_event_loop()
        queue: asyncio.Queue = asyncio.Queue()
        SENTINEL = object()

        def producer():
            try:
                for chunk in rag_chain.stream(question):  # type: ignore[union-attr]
                    text = chunk if isinstance(chunk, str) else str(chunk)
                    asyncio.run_coroutine_threadsafe(queue.put(text), loop)
            except Exception as e:
                asyncio.run_coroutine_threadsafe(
                    queue.put(json.dumps({"__error__": str(e)})),
                    loop,
                )
            finally:
                asyncio.run_coroutine_threadsafe(queue.put(SENTINEL), loop)

        threading.Thread(target=producer, daemon=True).start()

        try:
            while True:
                item = await queue.get()
                if item is SENTINEL:
                    break

                if isinstance(item, str) and item.startswith('{"__error__"'):
                    msg = json.loads(item).get("__error__", "Unknown error")
                    yield _sse(json.dumps({"type": "error", "message": msg}))
                    break

                token = item if isinstance(item, str) else str(item)
                if token:
                    yield _sse(json.dumps({"type": "token", "text": token}))
        finally:
            yield _sse(json.dumps({"type": "done"}))

    headers = {"Cache-Control": "no-cache", "Connection": "keep-alive"}
    return StreamingResponse(event_gen(), media_type="text/event-stream", headers=headers)
