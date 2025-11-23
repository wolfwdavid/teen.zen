import os
import shutil
import logging
from typing import Tuple, Optional, List

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_huggingface import HuggingFaceEmbeddings, HuggingFaceEndpoint
from langchain_community.vectorstores import Chroma
from langchain.prompts import PromptTemplate
from langchain.schema.runnable import RunnablePassthrough
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("chain")

RAG_PROMPT_TEMPLATE = """
You are a concise, helpful expert. Use ONLY the context below to answer.
- Do NOT repeat the user's question.
- Do NOT include banners, disclaimers, or system notes.
- Output ONLY the answer text (no bullets, no greetings, no "</s>").

Context:
{context}

User question: {question}
Answer:
"""

# --- config via env (safe defaults) ---
DOCS_DIR          = os.getenv("DOCS_DIR", "./docs")
CHROMA_DIR        = os.getenv("CHROMA_DIR", "./.chroma")   # persisted index location
CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "rag-index")

# smaller, CPU-friendly embeddings
EMBED_MODEL       = os.getenv("EMBED_MODEL", "BAAI/bge-small-en-v1.5")
FORCE_DEVICE      = os.getenv("EMBED_DEVICE", "").strip().lower()  # "cpu" or "cuda"

# TGI URL – you already have TinyLlama running here
TGI_URL           = os.getenv("TGI_URL", "http://127.0.0.1:8080/")

# generation settings
MAX_NEW_TOKENS     = int(os.getenv("MAX_NEW_TOKENS", "120"))
TEMPERATURE        = float(os.getenv("TEMPERATURE", "0.5"))
REPETITION_PENALTY = float(os.getenv("REPETITION_PENALTY", "1.03"))

CHUNK_SIZE    = int(os.getenv("CHUNK_SIZE", "800"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "80"))


def _pick_device() -> str:
    """Pick device for embeddings."""
    if FORCE_DEVICE in {"cpu", "cuda"}:
        return FORCE_DEVICE
    try:
        import torch  # noqa
        return "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:
        return "cpu"


def _load_documents(docs_dir: str):
    """
    Load .txt and .md recursively using lightweight loaders.
    Also ensure 'source' metadata exists for citations.
    """
    if not os.path.isdir(docs_dir):
        raise FileNotFoundError(
            f"Directory not found: '{docs_dir}'. "
            "Create it and add .txt/.md files."
        )

    loaders = [
        DirectoryLoader(
            docs_dir,
            glob="**/*.txt",
            loader_cls=TextLoader,
            show_progress=True,
        ),
        DirectoryLoader(
            docs_dir,
            glob="**/*.md",
            loader_cls=TextLoader,
            show_progress=True,
        ),
    ]

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )

    all_docs: List[Document] = []
    for ld in loaders:
        docs = ld.load()
        # make sure each doc has a 'source' field
        for d in docs:
            d.metadata = d.metadata or {}
            if "source" not in d.metadata or not d.metadata["source"]:
                # fall back to file path if present
                d.metadata["source"] = d.metadata.get("source") or d.metadata.get("file_path") or "unknown"
        if docs:
            all_docs.extend(splitter.split_documents(docs))

    if not all_docs:
        raise RuntimeError(
            f"No documents were found or split under '{docs_dir}'. "
            "Add at least one .txt or .md file with content."
        )

    logger.info("Loaded %d chunks from '%s'", len(all_docs), docs_dir)
    return all_docs


def _has_persist(path: str) -> bool:
    """Return True if the Chroma directory has any files (already persisted)."""
    return os.path.isdir(path) and any(True for _ in os.scandir(path))


def _build_vectorstore(embeddings: HuggingFaceEmbeddings):
    """
    Load an existing persisted Chroma DB (by collection) or build one if missing.
    """
    if _has_persist(CHROMA_DIR):
        logger.info(
            "Loading existing Chroma DB from '%s' (collection='%s') ...",
            CHROMA_DIR,
            CHROMA_COLLECTION,
        )
        try:
            return Chroma(
                persist_directory=CHROMA_DIR,
                collection_name=CHROMA_COLLECTION,
                embedding_function=embeddings,
            )
        except Exception as e:
            logger.warning("Failed to load persisted Chroma (%s). Rebuilding...", e)

    logger.info(
        "Creating new Chroma DB at '%s' (collection='%s') ...",
        CHROMA_DIR,
        CHROMA_COLLECTION,
    )
    docs = _load_documents(DOCS_DIR)
    vs = Chroma.from_documents(
        docs,
        embeddings,
        persist_directory=CHROMA_DIR,
        collection_name=CHROMA_COLLECTION,
    )
    vs.persist()
    logger.info("Persisted Chroma DB.")
    return vs


def build_rag_chain() -> Tuple[object, object]:
    """
    Build and return (rag_chain, retriever).
    """
    device = _pick_device()
    logger.info("Using embeddings model '%s' on device '%s'", EMBED_MODEL, device)

    embeddings = HuggingFaceEmbeddings(
        model_name=EMBED_MODEL,
        model_kwargs={"device": device},
        encode_kwargs={"normalize_embeddings": True},
    )

    vectorstore = _build_vectorstore(embeddings)

    # MMR retriever: better diversity with small prompt budget
    retriever = vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs={"k": 4, "fetch_k": 12, "lambda_mult": 0.5},
    )

    logger.info("Connecting to TGI at %s", TGI_URL)
    llm = HuggingFaceEndpoint(
        endpoint_url=TGI_URL,
        max_new_tokens=MAX_NEW_TOKENS,
        temperature=TEMPERATURE,
        repetition_penalty=REPETITION_PENALTY,
        stop=["</s>", "<|endoftext|>", "<|im_end|>"],
        streaming=True,
    )

    rag_prompt = PromptTemplate.from_template(RAG_PROMPT_TEMPLATE)
    # This chain supports .stream(question) which we use in api.py
    rag_chain = {"context": retriever, "question": RunnablePassthrough()} | rag_prompt | llm
    return rag_chain, retriever


def reindex_all() -> Tuple[object, object]:
    """
    Delete the persisted DB and rebuild from docs.
    """
    if os.path.isdir(CHROMA_DIR):
        logger.info("Deleting Chroma dir '%s' for full reindex ...", CHROMA_DIR)
        shutil.rmtree(CHROMA_DIR, ignore_errors=True)
    return build_rag_chain()


def get_sources(question: str, retriever_obj) -> list:
    """
    Return a list of citation dicts:
    [{ "source": str, "href": str | None, "preview": str | None }, ...]
    """
    sources = []
    try:
        # Using deprecated get_relevant_documents is fine for now
        docs: List[Document] = retriever_obj.get_relevant_documents(question)  # type: ignore[attr-defined]
    except Exception as e:
        logger.warning("get_sources failed: %s", e)
        return []

    for i, d in enumerate(docs):
        meta = d.metadata or {}
        src_label = meta.get("source") or f"doc_{i+1}"
        # If DOCS_DIR is served at /docs, build href relative to it
        file_path = meta.get("source") or meta.get("file_path")
        href = None
        if file_path and isinstance(file_path, str):
            # normalize path & strip DOCS_DIR prefix if present
            rel = os.path.relpath(file_path, DOCS_DIR) if os.path.isabs(file_path) or file_path.startswith(DOCS_DIR) else file_path
            href = f"/docs/{rel.replace(os.sep, '/')}"
        preview = (d.page_content or "").strip()
        if len(preview) > 200:
            preview = preview[:200] + "..."
        sources.append(
            {
                "source": src_label,
                "href": href,
                "preview": preview,
            }
        )
    return sources


# Optional eager build (disabled unless explicitly requested)
rag_chain: Optional[object] = None
retriever: Optional[object] = None

if os.getenv("EAGER_BUILD", "").lower() in {"1", "true", "yes"}:
    rag_chain, retriever = build_rag_chain()
