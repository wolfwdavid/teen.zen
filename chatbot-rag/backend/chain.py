import os
import shutil
import logging
from typing import Tuple, Optional, List, Dict

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_huggingface import HuggingFaceEmbeddings, HuggingFaceEndpoint
from langchain_community.vectorstores import Chroma
from langchain.prompts import PromptTemplate
from langchain.schema.runnable import RunnablePassthrough
from langchain.text_splitter import RecursiveCharacterTextSplitter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
DOCS_DIR           = os.getenv("DOCS_DIR", "./docs")
CHROMA_DIR         = os.getenv("CHROMA_DIR", "./.chroma")   # persisted index location
CHROMA_COLLECTION  = os.getenv("CHROMA_COLLECTION", "rag-index")

# smaller, faster default on CPU:
EMBED_MODEL        = os.getenv("EMBED_MODEL", "BAAI/bge-small-en-v1.5")
FORCE_DEVICE       = os.getenv("EMBED_DEVICE", "").strip().lower()  # "cpu" or "cuda"
TGI_URL            = os.getenv("TGI_URL", "http://127.0.0.1:8080/")

MAX_NEW_TOKENS     = int(os.getenv("MAX_NEW_TOKENS", "120"))  # shorter = faster
TEMPERATURE        = float(os.getenv("TEMPERATURE", "0.5"))
REPETITION_PENALTY = float(os.getenv("REPETITION_PENALTY", "1.03"))
CHUNK_SIZE         = int(os.getenv("CHUNK_SIZE", "800"))       # leaner chunks
CHUNK_OVERLAP      = int(os.getenv("CHUNK_OVERLAP", "80"))


def _pick_device() -> str:
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
    Also inject 'source' metadata to help with future citations.
    """
    if not os.path.isdir(docs_dir):
        raise FileNotFoundError(
            f"Directory not found: '{docs_dir}'. Create it and add .txt/.md files."
        )

    loaders = [
        DirectoryLoader(docs_dir, glob="**/*.txt", loader_cls=TextLoader, show_progress=True),
        DirectoryLoader(docs_dir, glob="**/*.md",  loader_cls=TextLoader, show_progress=True),
    ]

    splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    all_docs = []
    for ld in loaders:
        docs = ld.load()
        for d in docs:
            d.metadata = d.metadata or {}
            # ensure we always have some source
            d.metadata.setdefault("source", d.metadata.get("source") or "unknown")
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
    device = _pick_device()
    logger.info("Using embeddings model '%s' on device '%s'", EMBED_MODEL, device)

    embeddings = HuggingFaceEmbeddings(
        model_name=EMBED_MODEL,
        model_kwargs={"device": device},
        encode_kwargs={"normalize_embeddings": True},
    )

    vectorstore = _build_vectorstore(embeddings)

    # MMR: better relevance with a tight prompt budget
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
    rag_chain = {"context": retriever, "question": RunnablePassthrough()} | rag_prompt | llm
    return rag_chain, retriever


def reindex_all() -> Tuple[object, object]:
    """Delete the persisted Chroma DB and rebuild from docs."""
    if os.path.isdir(CHROMA_DIR):
        logger.info("Deleting Chroma dir '%s' for full reindex ...", CHROMA_DIR)
        shutil.rmtree(CHROMA_DIR, ignore_errors=True)
    return build_rag_chain()


def get_sources(question: str, retriever) -> List[Dict]:
    """
    Return a small list of citation objects:
    [{ "id": 1, "source": "...", "href": "/docs/...", "preview": "..." }, ...]
    """
    docs = retriever.get_relevant_documents(question)
    seen = set()
    out: List[Dict] = []
    for i, d in enumerate(docs, start=1):
        src = (d.metadata or {}).get("source", "unknown")
        if src in seen:
            continue
        seen.add(src)

        href = None
        # heuristic: if it looks like a local file, link to /docs
        base = os.path.basename(src)
        if base and "." in base:
            href = f"/docs/{base}"

        preview = (d.page_content or "").strip().replace("\n", " ")
        if len(preview) > 160:
            preview = preview[:157] + "..."

        out.append(
            {
                "id": i,
                "source": src,
                "href": href,
                "preview": preview,
            }
        )
    return out


# Optional eager build (disabled unless explicitly requested)
rag_chain: Optional[object] = None
retriever: Optional[object] = None

if os.getenv("EAGER_BUILD", "").lower() in {"1", "true", "yes"}:
    rag_chain, retriever = build_rag_chain()
