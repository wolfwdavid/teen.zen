import logging
import time
import json
import asyncio
import threading
from urllib.parse import unquote

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

import chain_v2  # ✅ import the module, not variables

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api_v2")

app = FastAPI(title="RAG Chatbot – V2 (BitNet 1.58b)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    question: str


@app.on_event("startup")
def on_startup():
    logger.info("🔧 Startup (V2): initializing RAG + model...")
    st = chain_v2.initialize_global_vars(force=False)
    logger.info("Startup state: %s", st)


@app.get("/health")
def health():
    return {
        "ok": True,
        "initialized": chain_v2.state.initialized,
        "model_loaded": chain_v2.state.model_loaded,
        "init_error": chain_v2.state.init_error,
        # extra debugging so you can see the mismatch if it ever happens again:
        "rag_chain_is_none": chain_v2.rag_chain is None,
        "retriever_is_none": chain_v2.retriever is None,
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


def _sse(data: str) -> str:
    return f"data: {data}\n\n"


@app.post("/chat")
async def chat(req: ChatRequest):
    _require_ready()
    question = (req.question or "").strip()

    srcs = chain_v2.get_sources(question, chain_v2.retriever)
    answer = chain_v2.rag_chain.invoke(question)
    return {"answer": answer, "sources": srcs}


@app.get("/chat/stream")
async def chat_stream(q: str):
    _require_ready()

    question = unquote(q or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="Missing query parameter 'q'")

    srcs = chain_v2.get_sources(question, chain_v2.retriever)

    async def event_gen():
        start_time = time.time()
        yield _sse(json.dumps({"type": "sources", "items": srcs}))

        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[str | None] = asyncio.Queue()

        def producer():
            try:
                for chunk in chain_v2.rag_chain.stream(question):
                    asyncio.run_coroutine_threadsafe(queue.put(chunk), loop)
            except Exception as e:
                logger.exception("Stream producer error: %s", e)
                asyncio.run_coroutine_threadsafe(queue.put(f"[error] {e}"), loop)
            finally:
                asyncio.run_coroutine_threadsafe(queue.put(None), loop)

        threading.Thread(target=producer, daemon=True).start()

        while True:
            item = await queue.get()
            if item is None:
                break
            yield _sse(json.dumps({"type": "token", "text": item}))

        elapsed = time.time() - start_time
        yield _sse(json.dumps({"type": "perf_time", "data": f"{elapsed:.2f}"}))
        yield _sse(json.dumps({"type": "done"}))

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
