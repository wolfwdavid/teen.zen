# backend/api.py
import os
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from chain import build_rag_chain, rag_chain as _rag_chain

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api")

app = FastAPI(title="RAG Chat API", version="1.0.0")

# Allow your Vite dev origin by default; override with FRONTEND_ORIGIN if needed
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global handles populated at startup
RAG = {"chain": None, "retriever": None}


class ChatRequest(BaseModel):
    question: str


@app.on_event("startup")
async def on_startup():
    """Build the RAG pipeline once at server start (lazy, safe)."""
    logger.info("🔧 Startup: building RAG chain...")
    try:
        # If chain was eagerly built via EAGER_BUILD, reuse it
        if _rag_chain is not None:
            RAG["chain"] = _rag_chain
            logger.info("♻️ Reusing eagerly built chain from module import.")
            return

        rag_chain, retriever = build_rag_chain()
        RAG["chain"] = rag_chain
        RAG["retriever"] = retriever
        logger.info("✅ RAG ready.")
    except Exception as e:
        logger.exception("❌ Failed to build RAG chain on startup: %s", e)
        # Keep API up so /health can report degraded status


@app.get("/health")
async def health():
    """Liveness/readiness probe with key config signals."""
    status = "ok" if RAG["chain"] is not None else "degraded"
    return {
        "status": status,
        "docs_dir": os.getenv("DOCS_DIR", "./docs"),
        "embed_model": os.getenv("EMBED_MODEL", "BAAI/bge-large-en-v1.5"),
        "embed_device": os.getenv("EMBED_DEVICE", "") or "auto",
        "tgi_url": os.getenv("TGI_URL", "http://0.0.0.0:8080/"),
        "max_new_tokens": int(os.getenv("MAX_NEW_TOKENS", "512")),
    }


@app.post("/chat")
async def chat(req: ChatRequest):
    """
    Chat endpoint (non-streaming). Returns a single string.
    503 if RAG not ready; 500 on generation failure.
    """
    if RAG["chain"] is None:
        raise HTTPException(
            status_code=503,
            detail="RAG not ready. Check /health and server logs.",
        )
    try:
        response = ""
        for chunk in RAG["chain"].stream(req.question):
            response += chunk
        return {"answer": response}
    except Exception as e:
        logger.exception("Error during chat generation: %s", e)
        raise HTTPException(status_code=500, detail="Chat generation failed.")


@app.post("/reindex")
async def reindex():
    """Rebuild docs/embeddings/vectorstore without restarting the server."""
    try:
        logger.info("🔁 Reindex requested: rebuilding RAG chain...")
        rag_chain, retriever = build_rag_chain()
        RAG["chain"] = rag_chain
        RAG["retriever"] = retriever
        logger.info("✅ Reindex complete.")
        return {"status": "ok", "message": "Reindex complete."}
    except Exception as e:
        logger.exception("Reindex failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Reindex failed: {e}")
