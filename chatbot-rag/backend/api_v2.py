import os
import logging
import time
from typing import Dict, Any, Generator # <-- Generator added here

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from langchain_core.runnables import RunnableConfig

# Import only the necessary components from chain_v2
from chain_v2 import (
    build_rag_chain,
    get_vector_store
    # Removed: reindex_all, which is no longer defined
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Initialization ---

# Initialize the FastAPI application
app = FastAPI(title="Chatbot RAG API V2")

# Configure CORS
origins = [
    "http://localhost",
    "http://localhost:5173",  # Assuming your React/Vite app runs here
    "http://127.0.0.0:5173",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables to hold the RAG chain and retriever instance
rag_chain = None
retriever = None

# --- Startup/Shutdown Events ---

@app.on_event("startup")
async def on_startup():
    """Initializes the RAG chain and model on application startup."""
    global rag_chain, retriever
    logger.info("🔧 Startup (V2): initializing RAG + ONNX...")
    try:
        # Load the RAG chain and vector store
        rag_chain, retriever = build_rag_chain()
        logger.info("✅ Startup (V2): RAG chain and model loaded successfully.")
    except Exception as e:
        # NOTE: This block is triggered by the ONNX/DML error you saw
        logger.error(f"❌ Failed to initialize RAG V2: {e}", exc_info=True)
        # Set chain to None to indicate failure, so the chat endpoint can report it.
        rag_chain = None

@app.on_event("shutdown")
async def on_shutdown():
    """Perform cleanup tasks on shutdown (optional, but good practice)."""
    logger.info("🧹 Shutdown (V2): Cleaning up resources...")
    pass

# --- Health Check ---

@app.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return {"status": "ok", "chain_loaded": rag_chain is not None}

# --- Chat Endpoint (SSE Streaming) ---

# CRITICAL FIX: The function must be a synchronous generator (def) and yield directly.
def stream_rag_response(question: str) -> Generator[Dict[str, Any], None, None]:
    """Generator function for streaming the RAG chain response."""
    global rag_chain, retriever

    if rag_chain is None:
        # This will be triggered if the startup failed
        yield {
            "type": "error",
            "message": "RAG model is not initialized or failed to load. Check server logs."
        }
        yield {"type": "end"}
        return

    # 1. Start timer
    start_time = time.time()
    
    # 2. Get the context (source documents)
    try:
        # Use a simplified search to get context before generation starts
        docs = retriever.invoke(question)
        context_sources = [{"source": doc.metadata.get('source', 'Unknown'), 
                            "page": doc.metadata.get('page', 'Unknown')} for doc in docs]
    except Exception as e:
        logger.error(f"Error retrieving context: {e}", exc_info=True)
        context_sources = []


    # 3. Yield the context/metadata package
    yield {
        "type": "context",
        "sources": context_sources,
        "latency": 0.0 # Will be updated in the 'end' event
    }

    # 4. Iterate through the LLM output (the generation phase)
    full_response = ""
    try:
        # The rag_chain.invoke is a blocking call, which is fine for a synchronous generator
        response = rag_chain.invoke(question)
        full_response = response.strip()
        
        # Simulate streaming by sending the whole response as one chunk
        yield {
            "type": "stream",
            "chunk": full_response
        }

    except Exception as e:
        error_message = f"An error occurred during generation: {e}"
        logger.error(error_message, exc_info=True)
        yield {
            "type": "error",
            "message": error_message
        }
    
    # 5. End event with timing
    end_time = time.time()
    yield {
        "type": "end",
        "latency": round(end_time - start_time, 2),
        "full_response": full_response,
        "sources": context_sources
    }


@app.get("/chat/stream")
async def chat_stream(q: str):
    """
    Endpoint for streaming RAG responses using Server-Sent Events (SSE).
    :param q: The user's question.
    """
    logger.info(f"Received stream request: {q}")
    # EventSourceResponse expects an iterable (which stream_rag_response now is).
    return EventSourceResponse(stream_rag_response(q))