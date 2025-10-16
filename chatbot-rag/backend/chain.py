import os
import shutil
import logging
from typing import Tuple, Optional

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
DOCS_DIR     = os.getenv("DOCS_DIR", "./docs")
CHROMA_DIR   = os.getenv("CHROMA_DIR", "./.chroma")  # ✅ persisted index location
EMBED_MODEL  = os.getenv("EMBED_MODEL", "BAAI/bge-large-en-v1.5")
FORCE_DEVICE = os.getenv("EMBED_DEVICE", "").strip().lower()  # "cpu" or "cuda"
TGI_URL      = os.getenv("TGI_URL", "http://127.0.0.1:8080/")  # connect addr

MAX_NEW_TOKENS      = int(os.getenv("MAX_NEW_TOKENS", "512"))
TEMPERATURE         = float(os.getenv("TEMPERATURE", "0.5"))
REPETITION_PENALTY  = float(os.getenv("REPETITION_PENALTY", "1.03"))
CHUNK_SIZE          = int(os.getenv("CHUNK_SIZE", "1024"))
CHUNK_OVERLAP       = int(os.getenv("CHUNK_OVERLAP", "128"))


def _pick_device() -> str:
    """Choose CUDA if available unless EMBED_DEVICE forces a value."""
    if FORCE_DEVICE in {"cpu", "cuda"}:
        return FORCE_DEVICE
    try:
        import torch  # noqa
        return "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:
        return "cpu"


def _load_documents(docs_dir: str):
    """
    Loads .txt and .md recursively using lightweight loaders (no 'unstructured' dep).
    """
    if not os.path.isdir(docs_dir):
        raise FileNotFoundError(f"Directory not found: '{docs_dir}'. Create it and add .txt/.md files.")

    loaders = [
        DirectoryLoader(docs_dir, glob="**/*.txt", loader_cls=TextLoader, show_progress=True),
        DirectoryLoader(docs_dir, glob="**/*.md",  loader_cls=TextLoader, show_progress=True),
    ]

    splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    all_docs = []
    for ld in loaders:
        docs = ld.load()
        if docs:
            all_docs.extend(splitter.split_documents(docs))

    if not all_docs:
        raise ValueError(
            f"No documents found under '{docs_dir}'. Add at least one .txt or .md file with content."
        )
    logger.info("Loaded %d chunks from '%s'", len(all_docs), docs_dir)
    return all_docs


def _has_persist(path: str) -> bool:
    """Return True if the Chroma directory has any files (already persisted)."""
    return os.path.isdir(path) and any(True for _ in os.scandir(path))


def _build_vectorstore(embeddings: HuggingFaceEmbeddings):
    """
    Load an existing persisted Chroma DB if present; otherwise build from docs and persist.
    """
    if _has_persist(CHROMA_DIR):
        logger.info("Loading existing Chroma DB from '%s' ...", CHROMA_DIR)
        return Chroma(persist_directory=CHROMA_DIR, embedding_function=embeddings)

    logger.info("Creating new Chroma DB at '%s' ...", CHROMA_DIR)
    docs = _load_documents(DOCS_DIR)
    vs = Chroma.from_documents(docs, embeddings, persist_directory=CHROMA_DIR)
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
    retriever = vectorstore.as_retriever()

    logger.info("Connecting to TGI at %s", TGI_URL)
    llm = HuggingFaceEndpoint(
    endpoint_url=TGI_URL,
    max_new_tokens=MAX_NEW_TOKENS,
    temperature=TEMPERATURE,
    repetition_penalty=REPETITION_PENALTY,
    streaming=True,
    stop_sequences=["</s>", "<|endoftext|>", "<|im_end|>"],  # ⬅️ add this
)


    rag_prompt = PromptTemplate.from_template(RAG_PROMPT_TEMPLATE)
    rag_chain = {"context": retriever, "question": RunnablePassthrough()} | rag_prompt | llm
    return rag_chain, retriever


def reindex_all() -> Tuple[object, object]:
    """
    Delete the persisted DB and rebuild from docs. Useful for a /reindex endpoint.
    """
    if os.path.isdir(CHROMA_DIR):
        logger.info("Deleting Chroma dir '%s' for full reindex ...", CHROMA_DIR)
        shutil.rmtree(CHROMA_DIR, ignore_errors=True)
    return build_rag_chain()


# Optional eager build (disabled unless explicitly requested)
rag_chain: Optional[object] = None
retriever: Optional[object] = None

if os.getenv("EAGER_BUILD", "").lower() in {"1", "true", "yes"}:
    rag_chain, retriever = build_rag_chain()
