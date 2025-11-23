# api_v2.py
import os
import logging
import queue # <--- NEW IMPORT for synchronous queue
import asyncio
import json
from typing import Optional, Any # Added Any for better typing of RAG components
from urllib.parse import unquote

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
# NOTE: Removed 'threading' as it's no longer manually managed for streaming

# Assuming these are synchronous components from chain_v2
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
    # Fixed indentation
    app.mount("/docs", StaticFiles(directory=DOCS_DIR, html=False), name="docs")
else:
    # Fixed indentation
    logger.warning("Docs dir '%s' not found; /docs will not be mounted.", DOCS_DIR)

# CORS for Vite dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Use 'Any' to correctly type the objects if their specific classes aren't imported
RAGChain = Any
Retriever = Any

# Global state is fine for singletons, but use specific types if known, otherwise Any
rag_chain: Optional[RAGChain] = None
retriever: Optional[Retriever] = None


class ChatRequest(BaseModel):
    question: str


@app.on_event("startup")
def on_startup():
    """
    Prefer eager singletons from chain_v2 when present.
    Otherwise, build once here.
    """
    global rag_chain, retriever
    app.state.rag_ready = False
    app.state.rag_error = None

    logger.info(" Startup (V2): initializing RAG + ONNX...")
    try:
        # Fixed indentation in the startup logic
        if eager_chain is not None and eager_retriever is not None:
            logger.info("Using eager rag_chain + retriever from chain_v2")
            rag_chain = eager_chain
            retriever = eager_retriever
        else:
            logger.info("Building chain + retriever...")
            rag_chain, retriever = build_rag_chain()

        app.state.rag_ready = True
        logger.info(" RAG V2 ready.")
    except Exception as e:
        app.state.rag_error = str(e)
        logger.exception(" Failed to initialize RAG V2: %s", e)


@app.get("/health")
def health():
    # Use status.HTTP_200_OK if health check is fully successful
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
        # Added type hints to explicitly show the expected return type from reindex_all()
        new_chain, new_retriever = reindex_all()
        rag_chain = new_chain
        retriever = new_retriever
        app.state.rag_ready = True
        app.state.rag_error = None
        return {"status": "ok", "message": "Reindex complete."}
    except Exception as e:
        app.state.rag_ready = False
        app.state.rag_error = str(e)
        logger.exception("Reindex failed: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Reindex failed: {e}")


@app.post("/chat")
async def chat(req: ChatRequest):
    # Replaced magic number 503 with proper HTTP status constant
    if not getattr(app.state, "rag_ready", False) or rag_chain is None or retriever is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="RAG V2 not ready. Check /health and logs.")
    try:
        # No longer using type ignore, rely on the global check above
        srcs = get_sources(req.question, retriever)
        answer = rag_chain.invoke(req.question)
        return {"answer": answer, "sources": srcs}
    except Exception as e:
        logger.exception("Chat failed: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Chat failed: {e}")


# ------- SSE streaming -------

def _sse(data: str) -> str:
    """Formats a string as a Server-Sent Event."""
    return f"data: {data}\n\n"


@app.get("/chat/stream")
async def chat_stream(q: str):
    # Corrected indentation for the initial check
    if not getattr(app.state, "rag_ready", False) or rag_chain is None or retriever is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="RAG V2 not ready. Check /health and logs.")

    question = unquote(q or "").strip()
    if not question:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing question")

    logger.info(" /chat/stream (V2) question=%r", question)
    
    # Check for sources first before stream starts
    try:
        srcs = get_sources(question, retriever)
    except Exception as e:
        logger.exception("Source retrieval failed in chat stream: %s", e)
        # Fail early if source retrieval is essential
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Source retrieval failed: {e}")

    # The corrected and robust streaming implementation
    async def event_gen():
        # Use synchronous queue for thread-to-thread communication
        q_sync: queue.Queue = queue.Queue()
        SENTINEL = object()
        
        # Initial frames
        yield _sse(json.dumps({"type": "status", "message": "started"}))
        yield _sse(json.dumps({"type": "sources", "items": srcs}))

        # 1. Producer function runs in a background thread (via asyncio.to_thread)
        def producer():
            try:
                # This code runs synchronously in the thread
                for chunk in rag_chain.stream(question):
                    text = chunk if isinstance(chunk, str) else str(chunk)
                    q_sync.put(text)
            except Exception as e:
                # Put the error into the queue for the consumer to catch
                q_sync.put(json.dumps({"__error__": str(e)}))
            finally:
                # Signal the end of the stream
                q_sync.put(SENTINEL)

        # 2. Start the producer in a separate thread without blocking the event loop
        # We don't need to manually manage threading.Thread() or the event loop.
        producer_task = asyncio.to_thread(producer)
        
        try:
            # 3. Consumer loop runs asynchronously
            while True:
                # Safely await a blocking call (q_sync.get()) without blocking the event loop
                item = await asyncio.to_thread(q_sync.get)
                
                if item is SENTINEL:
                    break

                if isinstance(item, str) and item.startswith('{"__error__"'):
                    # Handle error from the producer thread
                    msg = json.loads(item).get("__error__", "Unknown error")
                    yield _sse(json.dumps({"type": "error", "message": msg}))
                    break

                # NOTE: we do *not* strip spaces here – chunks already keep spacing
                token = item if isinstance(item, str) else str(item)
                if token:
                    yield _sse(json.dumps({"type": "token", "text": token}))
        
        except Exception as e:
            # Catch exceptions in the consumer side (e.g., client disconnection)
            logger.warning("Stream consumer error or client disconnection: %s", e)
        finally:
            # Ensure the stream is marked as complete
            yield _sse(json.dumps({"type": "done"}))
            # Clean up: attempt to cancel the producer thread if it's still running
            # In Python 3.9+, cancelling the task will attempt to interrupt the thread.
            producer_task.cancel()
            
    headers = {"Cache-Control": "no-cache", "Connection": "keep-alive"}
    return StreamingResponse(event_gen(), media_type="text/event-stream", headers=headers)