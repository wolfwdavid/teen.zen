import logging
import time
import json
import asyncio
import threading
from urllib.parse import unquote
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

import chain_v2  # import the module, not variables

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api_v2")

app = FastAPI(title="RAG Chatbot – V2")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


class ChatRequest(BaseModel):
    question: str
    k: Optional[int] = None  # optional override


@app.on_event("startup")
def on_startup():
    logger.info("🔧 Startup (V2): initializing RAG + model...")
    st = chain_v2.initialize_global_vars(force=False)
    logger.info("Startup state: %s", st)


@app.get("/health")
def health():
    vectorstore_is_none = getattr(chain_v2, "vectorstore", None) is None

    return {
        "ok": True,
        "initialized": chain_v2.state.initialized,
        "model_loaded": chain_v2.state.model_loaded,
        "init_error": chain_v2.state.init_error,
        "rag_chain_is_none": chain_v2.rag_chain is None,
        "retriever_is_none": chain_v2.retriever is None,
        "vectorstore_is_none": vectorstore_is_none,
    }


def _require_ready():
    if (not chain_v2.state.model_loaded) or (chain_v2.rag_chain is None) or (chain_v2.retriever is None):
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Model not loaded",
                "initialized": chain_v2.state.initialized,
                "model_loaded": chain_v2.state.model_loaded,
                "init_error": chain_v2.state.init_error,
                "rag_chain_is_none": chain_v2.rag_chain is None,
                "retriever_is_none": chain_v2.retriever is None,
            },
        )


def _sse(obj) -> str:
    return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"


@app.post("/chat")
async def chat(req: ChatRequest):
    _require_ready()

    question = (req.question or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="Missing 'question'")

    k = int(req.k) if req.k else 3

    # 1) Generate answer first (chain_v2 already gates: returns "I don't know." if no relevant context)
    answer = chain_v2.rag_chain.invoke(question)

    # 2) Only return sources if we actually answered
    if answer.strip() == "I don't know.":
        return {"answer": answer, "sources": []}

    # chain_v2.get_sources signature: get_sources(question, k=...)
    srcs = chain_v2.get_sources(question, k=k)
    return {"answer": answer, "sources": srcs}


@app.get("/chat/stream")
async def chat_stream(
    request: Request,
    q: str = Query(..., description="User question"),
    k: int = Query(3, ge=1, le=20, description="Top-K sources to retrieve"),
    debug: int = Query(0, ge=0, le=1, description="Include extra debug fields in SSE payloads"),
    heartbeat: float = Query(0.0, ge=0.0, le=10.0, description="Heartbeat seconds (0 disables)"),
):
    _require_ready()

    question = unquote(q or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="Missing query parameter 'q'")

    async def event_gen():
        start_time = time.time()

        # IMPORTANT: determine relevance by asking chain first (it will gate to "I don't know.")
        # We do this so we can return empty sources when gated.
        # (If you want to avoid double compute, we can optimize later.)
        gated_answer = chain_v2.rag_chain.invoke(question)

        if gated_answer.strip() == "I don't know.":
            # Sources first
            yield _sse({"type": "sources", "items": []})
            # Answer as one token chunk
            yield _sse({"type": "token", "text": "I don't know."})
            elapsed = time.time() - start_time
            yield _sse({"type": "perf_time", "data": f"{elapsed:.2f}"})
            yield _sse({"type": "done"})
            return

        # If we will answer, send sources (scored) first
        srcs = chain_v2.get_sources(question, k=k)
        payload = {"type": "sources", "items": srcs}
        if debug:
            payload["debug"] = {
                "k": k,
                "initialized": chain_v2.state.initialized,
                "model_loaded": chain_v2.state.model_loaded,
                "init_error": chain_v2.state.init_error,
            }
        yield _sse(payload)

        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[Optional[str]] = asyncio.Queue()
        stop_flag = threading.Event()

        def producer():
            try:
                # stream tokens from chain (uses the same gating internally)
                for chunk in chain_v2.rag_chain.stream(question):
                    if stop_flag.is_set():
                        break
                    asyncio.run_coroutine_threadsafe(queue.put(chunk), loop)
            except Exception as e:
                logger.exception("Stream producer error: %s", e)
                asyncio.run_coroutine_threadsafe(queue.put(f"[error] {e}"), loop)
            finally:
                asyncio.run_coroutine_threadsafe(queue.put(None), loop)

        threading.Thread(target=producer, daemon=True).start()

        last_heartbeat = time.time()

        while True:
            if await request.is_disconnected():
                stop_flag.set()
                break

            if heartbeat and (time.time() - last_heartbeat) >= heartbeat:
                last_heartbeat = time.time()
                yield ":\n\n"  # SSE comment heartbeat

            try:
                item = await asyncio.wait_for(queue.get(), timeout=0.25)
            except asyncio.TimeoutError:
                continue

            if item is None:
                break

            yield _sse({"type": "token", "text": item})

        elapsed = time.time() - start_time
        yield _sse({"type": "perf_time", "data": f"{elapsed:.2f}"})
        yield _sse({"type": "done"})

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
