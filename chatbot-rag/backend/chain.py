import os
import logging
from typing import Tuple, Optional

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEndpoint
from langchain.prompts import PromptTemplate
from langchain.schema.runnable import RunnablePassthrough
from langchain.text_splitter import RecursiveCharacterTextSplitter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

RAG_PROMPT_TEMPLATE = """
Here is context from documents that may be useful:
{context}

Answer the question as a helpful expert. Use only the context above.
User: {question}
Assistant:
"""

# --- config via env (safe defaults) ---
DOCS_DIR = os.getenv("DOCS_DIR", "./docs")
EMBED_MODEL = os.getenv("EMBED_MODEL", "BAAI/bge-large-en-v1.5")
FORCE_DEVICE = os.getenv("EMBED_DEVICE", "").strip().lower()  # set to "cpu" to force CPU
TGI_URL = os.getenv("TGI_URL", "http://0.0.0.0:8080/")

MAX_NEW_TOKENS = int(os.getenv("MAX_NEW_TOKENS", "512"))
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.5"))
REPETITION_PENALTY = float(os.getenv("REPETITION_PENALTY", "1.03"))
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1024"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "128"))


def _pick_device() -> str:
    """Choose CUDA if available unless EMBED_DEVICE forces a value."""
    if FORCE_DEVICE in {"cpu", "cuda"}:
        return FORCE_DEVICE
    try:
        import torch  # noqa
        import torch.cuda  # noqa
        return "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:
        # if torch isn't present (or crashes), just use cpu
        return "cpu"


def _load_documents(docs_dir: str):
    """
    Lightweight loaders that don't require 'unstructured'.
    Loads .txt and .md recursively.
    """
    if not os.path.isdir(docs_dir):
        raise FileNotFoundError(f"Directory not found: '{docs_dir}'. Create it and add .txt/.md files.")
    # Load .txt and .md via TextLoader (no heavy deps)
    loaders = [
        DirectoryLoader(docs_dir, glob="**/*.txt", loader_cls=TextLoader, show_progress=True),
        DirectoryLoader(docs_dir, glob="**/*.md", loader_cls=TextLoader, show_progress=True),
    ]

    splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    all_docs = []
    for ld in loaders:
        docs = ld.load()
        if docs:
            all_docs.extend(splitter.split_documents(docs))

    if not all_docs:
        raise ValueError(
            f"No documents found under '{docs_dir}'. "
            "Add at least one .txt or .md file with content."
        )
    logger.info("Loaded %d chunks from '%s'", len(all_docs), docs_dir)
    return all_docs


def build_rag_chain() -> Tuple[object, object]:
    """
    Build and return (rag_chain, retriever).
    Done lazily to avoid import-time crashes (e.g., Torch/CUDA segfaults).
    """
    # 1) docs -> vector store
    docs = _load_documents(DOCS_DIR)

    device = _pick_device()
    logger.info("Using embeddings model '%s' on device '%s'", EMBED_MODEL, device)

    embeddings = HuggingFaceEmbeddings(
        model_name=EMBED_MODEL,
        model_kwargs={"device": device},
        encode_kwargs={"normalize_embeddings": True},
    )

    vectorstore = Chroma.from_documents(docs, embeddings)
    retriever = vectorstore.as_retriever()

    # 2) LLM (HuggingFace TGI)
    logger.info("Connecting to TGI at %s", TGI_URL)
    llm = HuggingFaceTextGenInference(
        inference_server_url=TGI_URL,
        max_new_tokens=MAX_NEW_TOKENS,
        temperature=TEMPERATURE,
        repetition_penalty=REPETITION_PENALTY,
        streaming=True,
    )

    # 3) Prompt & chain
    rag_prompt = PromptTemplate.from_template(RAG_PROMPT_TEMPLATE)
    rag_chain = {"context": retriever, "question": RunnablePassthrough()} | rag_prompt | llm

    return rag_chain, retriever


# Optional: build once at import time if you want.
# Safer: import this module, then call build_rag_chain() from your FastAPI startup.
# Example in api.py:
#   rag_chain, retriever = build_rag_chain()
rag_chain: Optional[object] = None
retriever: Optional[object] = None

if os.getenv("EAGER_BUILD", "").lower() in {"1", "true", "yes"}:
    # Only build eagerly if explicitly requested
    rag_chain, retriever = build_rag_chain()
