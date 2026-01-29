import os
import logging
import time
import json
import asyncio
import threading
from urllib.parse import unquote
from typing import Optional, Any, Dict, List, Union

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

# ------------------------------------------------------------------------------
# CORS (✅ Android/Capacitor safe)
# ------------------------------------------------------------------------------
# IMPORTANT:
# - If allow_credentials=True, allow_origins cannot be ["*"].
# - EventSource/fetch from Capacitor typically uses origin "capacitor://localhost".
#
# Configure via env:
#   CORS_ORIGINS="http://localhost:5173,http://127.0.0.1:5173,capacitor://localhost"
#
cors_env = (os.getenv("CORS_ORIGINS") or "").strip()
if cors_env:
    ALLOW_ORIGINS = [o.strip() for o in cors_env.split(",") if o.strip()]
else:
    # Safe defaults for local dev + Capacitor
    ALLOW_ORIGINS = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost",
        "http://127.0.0.1",
        "capacitor://localhost",
        "ionic://localhost",
    ]

ALLOW_CREDENTIALS = os.getenv("CORS_ALLOW_CREDENTIALS", "1") == "1"

# If user *forces* wildcard, we must disable credentials or browsers reject it.
if "*" in ALLOW_ORIGINS and ALLOW_CREDENTIALS:
    logger.warning("CORS: '*' cannot be used with allow_credentials=True. Disabling credentials.")
    ALLOW_CREDENTIALS = False

app.add_middleware(
   CORSMiddleware,
    # ✅ Allow all origins safely by NOT using credentials
    allow_origins=["*"],
    allow_credentials=False,  # ✅ IMPORTANT
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

logger.info("CORS allow_origins=%s allow_credentials=%s", ALLOW_ORIGINS, ALLOW_CREDENTIALS)


# ------------------------------------------------------------------------------
# Models
# ------------------------------------------------------------------------------
class ChatRequest(BaseModel):
    question: str
    k: Optional[int] = None  # optional override


# ------------------------------------------------------------------------------
# Startup
# ------------------------------------------------------------------------------
@app.on_event("startup")
def on_startup():
    logger.info("🔧 Startup (V2): initializing RAG + model...")
    st = chain_v2.initialize_global_vars(force=False)
    logger.info("Startup state: %s", st)


# ------------------------------------------------------------------------------
# Health
# ------------------------------------------------------------------------------
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


def _sse(obj: Dict[str, Any]) -> str:
    return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"


def _get_sources_safe(question: str, k: int) -> List[Dict[str, Any]]:
    """
    Supports both chain_v2.get_sources signatures:
      - get_sources(question, k=...)
      - get_sources(question, retriever, k=...)
    """
    try:
        return chain_v2.get_sources(question, k=k)  # newer signature
    except TypeError:
        return chain_v2.get_sources(question, chain_v2.retriever, k=k)  # older signature


# ------------------------------------------------------------------------------
# POST /chat
# ------------------------------------------------------------------------------
@app.post("/chat")
async def chat(req: ChatRequest):
    _require_ready()

    question = (req.question or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="Missing 'question'")

    k = int(req.k) if req.k is not None else 3

    # Generate answer (chain_v2 already gates to "I don't know." when irrelevant)
    answer = chain_v2.rag_chain.invoke(question)

    # Only return sources if we actually answered
    if answer.strip() == "I don't know.":
        return {"answer": answer, "sources": []}

    srcs = _get_sources_safe(question, k=k)
    return {"answer": answer, "sources": srcs}


# ------------------------------------------------------------------------------
# GET /chat/stream (SSE)
# ------------------------------------------------------------------------------
@app.get("/chat/stream")
async def chat_stream(
    request: Request,
    q: str = Query(..., description="User question"),
    k: int = Query(3, ge=1, le=20, description="Top-K sources to retrieve"),
    debug: int = Query(0, ge=0, le=1, description="Include extra debug fields in SSE payloads"),
    heartbeat: float = Query(2.0, ge=0.0, le=10.0, description="Heartbeat seconds (0 disables)"),
):
    _require_ready()

    question = unquote(q or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="Missing query parameter 'q'")

    async def event_gen():
        start_time = time.time()

        # Gate once up front
        gated_answer = chain_v2.rag_chain.invoke(question)

        # Always send sources first (empty if gated)
        if gated_answer.strip() == "I don't know.":
            yield _sse({"type": "sources", "items": []})
            yield _sse({"type": "token", "text": "I don't know."})
            elapsed = time.time() - start_time
            yield _sse({"type": "perf_time", "data": f"{elapsed:.2f}"})
            yield _sse({"type": "done"})
            return

        # Send sources (scored) first
        try:
            srcs = _get_sources_safe(question, k=k)
        except Exception as e:
            srcs = []
            logger.exception("get_sources failed: %s", e)

        payload: Dict[str, Any] = {"type": "sources", "items": srcs}
        if debug:
            payload["debug"] = {
                "k": k,
                "initialized": chain_v2.state.initialized,
                "model_loaded": chain_v2.state.model_loaded,
                "init_error": chain_v2.state.init_error,
            }
        yield _sse(payload)

        # Stream tokens in a background thread -> async queue
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[Optional[Union[str, Dict[str, Any]]]] = asyncio.Queue()
        stop_flag = threading.Event()

        def producer():
            try:
                for chunk in chain_v2.rag_chain.stream(question):
                    if stop_flag.is_set():
                        break
                    asyncio.run_coroutine_threadsafe(queue.put(str(chunk)), loop)
            except Exception as e:
                logger.exception("Stream producer error: %s", e)
                asyncio.run_coroutine_threadsafe(queue.put({"type": "error", "error": str(e)}), loop)
            finally:
                asyncio.run_coroutine_threadsafe(queue.put(None), loop)

        threading.Thread(target=producer, daemon=True).start()

        last_heartbeat = time.time()

        while True:
            # client disconnected
            if await request.is_disconnected():
                stop_flag.set()
                break

            # heartbeat (SSE comment)
            if heartbeat and (time.time() - last_heartbeat) >= heartbeat:
                last_heartbeat = time.time()
                yield ":\n\n"

            try:
                item = await asyncio.wait_for(queue.get(), timeout=0.25)
            except asyncio.TimeoutError:
                continue

            if item is None:
                break

            # item may be token string or {"type":"error",...}
            if isinstance(item, dict):
                yield _sse(item)
                continue

            yield _sse({"type": "token", "text": item})

        elapsed = time.time() - start_time
        yield _sse({"type": "perf_time", "data": f"{elapsed:.2f}"})
        yield _sse({"type": "done"})

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
