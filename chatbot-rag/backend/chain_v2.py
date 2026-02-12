import os
import shutil
import logging
import json
import time
import warnings
from dataclasses import dataclass
from typing import Tuple, Optional, List, Dict, Any

# ------------------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    force=True,
)
logger = logging.getLogger("RAG_CHAIN")

print("\n" + "=" * 50, flush=True)
print("🚀 CHAIN_V2 MODULE LOADED", flush=True)
print("=" * 50 + "\n", flush=True)

# ------------------------------------------------------------------------------
# Third-party imports
# ------------------------------------------------------------------------------
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_chroma import Chroma
from sentence_transformers import SentenceTransformer
from langchain_core.embeddings import Embeddings
from typing import List as ListType

class HuggingFaceEmbeddings(Embeddings):
    """Custom wrapper for HuggingFace embeddings using sentence-transformers directly"""
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2", **kwargs):
        self.model = SentenceTransformer(model_name)

    def embed_documents(self, texts: ListType[str]) -> ListType[ListType[float]]:
        return self.model.encode(texts, convert_to_tensor=False).tolist()

    def embed_query(self, text: str) -> ListType[float]:
        return self.model.encode([text], convert_to_tensor=False)[0].tolist()

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

warnings.filterwarnings("ignore", category=UserWarning)

# llama-cpp-python
try:
    from llama_cpp import Llama
    LLAMA_CPP_AVAILABLE = True
except ImportError:
    LLAMA_CPP_AVAILABLE = False
    logger.warning("⚠️ llama-cpp-python not installed. Run: pip install llama-cpp-python")

# ------------------------------------------------------------------------------
# Config
# ------------------------------------------------------------------------------
DOCS_DIR = os.getenv("DOCS_DIR", "./docs")
CHROMA_DIR = os.getenv("CHROMA_DIR", "./.chroma")
CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "rag-index")
EMBED_MODEL = os.getenv("EMBED_MODEL", "BAAI/bge-small-en-v1.5")

# Model path
GGUF_MODEL_PATH = os.getenv(
    "GGUF_MODEL_PATH",
    "./models/qwen-1.5b/qwen2.5-1.5b-instruct-q4_k_m.gguf"
)

# Generation config
GEN_MAX_NEW_TOKENS = int(os.getenv("GEN_MAX_NEW_TOKENS", "256"))
GEN_TEMPERATURE = float(os.getenv("GEN_TEMPERATURE", "0.7"))
GEN_TOP_P = float(os.getenv("GEN_TOP_P", "0.9"))
GEN_CTX_SIZE = int(os.getenv("GEN_CTX_SIZE", "2048"))

# Retrieval config
RETRIEVAL_K_DEFAULT = int(os.getenv("RETRIEVAL_K", "3"))
MIN_RELEVANCE_SCORE = float(os.getenv("MIN_RELEVANCE_SCORE", "0.20"))
MAX_DISTANCE_SCORE = float(os.getenv("MAX_DISTANCE_SCORE", "1.25"))

# ------------------------------------------------------------------------------
# System prompt — Teen Zen mental health counselor
# ------------------------------------------------------------------------------
SYSTEM_PROMPT = """You are Teen Zen, a warm and empathetic mental health counselor for teenagers. 

YOUR GUIDELINES:
- Be supportive, compassionate, and non-judgmental
- Use age-appropriate language that teens can relate to
- Validate feelings before offering advice
- Suggest healthy coping strategies when appropriate
- Keep responses concise (2-4 sentences) unless more detail is needed
- If someone mentions self-harm or suicide, take it seriously and encourage them to reach out to a trusted adult or crisis helpline (988 Suicide & Crisis Lifeline)
- Never diagnose conditions — you are a supportive counselor, not a doctor
- If you have relevant context from documents, use it to ground your response
- If you don't know something, say so honestly

You care deeply about each teen you talk to."""

RAG_SYSTEM_PROMPT = """You are Teen Zen, a warm and empathetic mental health counselor for teenagers.

Use the following reference information to help answer the question. If the reference doesn't contain relevant information, rely on your general knowledge about teen mental health.

REFERENCE INFORMATION:
{context}

YOUR GUIDELINES:
- Be supportive, compassionate, and non-judgmental
- Use age-appropriate language that teens can relate to
- Validate feelings before offering advice
- Suggest healthy coping strategies when appropriate
- Keep responses concise (2-4 sentences) unless more detail is needed
- If someone mentions self-harm or suicide, take it seriously and encourage them to reach out to a trusted adult or crisis helpline (988 Suicide & Crisis Lifeline)
- Never diagnose conditions — you are a supportive counselor, not a doctor"""

# ------------------------------------------------------------------------------
# Global state
# ------------------------------------------------------------------------------
@dataclass
class ServiceState:
    initialized: bool = False
    model_loaded: bool = False
    init_error: Optional[str] = None


state = ServiceState()
rag_chain: Optional["RAGChain"] = None
retriever: Optional[BaseRetriever] = None
vectorstore: Optional[Chroma] = None

# Debug
try:
    print("CHAIN_V2 PATH =", os.path.abspath(__file__), flush=True)
except Exception:
    pass
print("DOCS_DIR =", os.path.abspath(DOCS_DIR), flush=True)
print("CHROMA_DIR =", os.path.abspath(CHROMA_DIR), flush=True)
print("GGUF_MODEL =", os.path.abspath(GGUF_MODEL_PATH), flush=True)

# ------------------------------------------------------------------------------
# Document loading & vectorstore
# ------------------------------------------------------------------------------
def _load_documents(docs_dir: str) -> List[Document]:
    os.makedirs(docs_dir, exist_ok=True)
    loaders = [
        DirectoryLoader(docs_dir, glob="**/*.txt", loader_cls=TextLoader),
        DirectoryLoader(docs_dir, glob="**/*.md", loader_cls=TextLoader),
    ]
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=80)

    all_docs: List[Document] = []
    for ld in loaders:
        try:
            docs = ld.load()
            all_docs.extend(splitter.split_documents(docs))
        except Exception as e:
            logger.warning("⚠️ Document loader failed: %s", e)

    if not all_docs:
        logger.warning("⚠️ No documents found in DOCS_DIR=%s", docs_dir)
        return []
    return all_docs


def _build_vectorstore(embeddings: HuggingFaceEmbeddings) -> Chroma:
    if os.path.isdir(CHROMA_DIR) and any(os.scandir(CHROMA_DIR)):
        logger.info("📚 [Chroma] Loading persisted index at: %s", CHROMA_DIR)
        return Chroma(
            persist_directory=CHROMA_DIR,
            collection_name=CHROMA_COLLECTION,
            embedding_function=embeddings,
        )

    logger.info("📚 [Chroma] Building new index from docs at: %s", DOCS_DIR)
    docs = _load_documents(DOCS_DIR)

    if not docs:
        logger.warning("⚠️ [Chroma] No docs to index. Creating empty collection.")
        vs = Chroma(
            persist_directory=CHROMA_DIR,
            collection_name=CHROMA_COLLECTION,
            embedding_function=embeddings,
        )
        try:
            vs.persist()
        except Exception:
            pass
        return vs

    vs = Chroma.from_documents(
        docs, embeddings,
        persist_directory=CHROMA_DIR,
        collection_name=CHROMA_COLLECTION,
    )
    try:
        vs.persist()
    except Exception:
        pass
    return vs


# ------------------------------------------------------------------------------
# Scored retrieval
# ------------------------------------------------------------------------------
def retrieve_with_scores(question: str, k: int = RETRIEVAL_K_DEFAULT) -> Dict[str, Any]:
    if vectorstore is None:
        return {"docs": [], "score_type": "none", "scores": []}

    if hasattr(vectorstore, "similarity_search_with_relevance_scores"):
        try:
            pairs = vectorstore.similarity_search_with_relevance_scores(question, k=k)
            docs = [d for d, _ in pairs]
            scores = [float(s) for _, s in pairs]
            return {"docs": docs, "score_type": "relevance", "scores": scores}
        except Exception as e:
            logger.warning("⚠️ [Retrieval] relevance_scores failed: %s", e)

    if hasattr(vectorstore, "similarity_search_with_score"):
        try:
            pairs = vectorstore.similarity_search_with_score(question, k=k)
            docs = [d for d, _ in pairs]
            scores = [float(s) for _, s in pairs]
            return {"docs": docs, "score_type": "distance", "scores": scores}
        except Exception as e:
            logger.warning("⚠️ [Retrieval] with_score failed: %s", e)

    try:
        docs = vectorstore.similarity_search(question, k=k)
        return {"docs": docs, "score_type": "none", "scores": [None] * len(docs)}
    except Exception:
        return {"docs": [], "score_type": "none", "scores": []}


def retrieval_is_relevant(score_type: str, scores: List[Any], docs: Optional[List[Document]] = None) -> bool:
    docs = docs or []
    if not docs:
        return False

    if score_type == "none" or not scores:
        joined = "\n".join([d.page_content.strip() for d in docs if d.page_content])
        return len(joined.strip()) >= 40

    if score_type == "relevance":
        try:
            return float(scores[0]) >= MIN_RELEVANCE_SCORE
        except Exception:
            return False

    if score_type == "distance":
        try:
            return float(scores[0]) <= MAX_DISTANCE_SCORE
        except Exception:
            return False

    return False


# ------------------------------------------------------------------------------
# LLM Model (Qwen via llama-cpp-python)
# ------------------------------------------------------------------------------
class QwenChatModel:
    def __init__(self, model_path: str):
        self.model = None
        self.last_error: Optional[str] = None

        if not LLAMA_CPP_AVAILABLE:
            self.last_error = "llama-cpp-python not installed"
            logger.error("❌ [LLM] %s", self.last_error)
            return

        if not os.path.isfile(model_path):
            self.last_error = f"Model file not found: {model_path}"
            logger.error("❌ [LLM] %s", self.last_error)
            return

        try:
            logger.info("📦 [LLM] Loading GGUF model: %s", model_path)
            self.model = Llama(
                model_path=model_path,
                n_ctx=GEN_CTX_SIZE,
                verbose=False,
            )
            logger.info("✅ [LLM] Model loaded successfully.")
        except Exception as e:
            self.last_error = str(e)
            logger.critical("❌ [LLM] Failed to load model: %s", e, exc_info=True)
            self.model = None

    def generate(self, question: str, system_prompt: str = SYSTEM_PROMPT) -> str:
        if self.model is None:
            return f"I'm sorry, I'm having trouble right now. Please try again later."

        try:
            response = self.model.create_chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": question},
                ],
                max_tokens=GEN_MAX_NEW_TOKENS,
                temperature=GEN_TEMPERATURE,
                top_p=GEN_TOP_P,
                stop=["<|im_end|>", "<|endoftext|>"],
            )
            text = response['choices'][0]['message']['content'].strip()
            return text if text else "I'm not sure how to respond to that. Could you tell me more?"
        except Exception as e:
            logger.error("❌ [LLM] Generation error: %s", e, exc_info=True)
            return "I'm sorry, I'm having trouble right now. Please try again later."

    def stream(self, question: str, system_prompt: str = SYSTEM_PROMPT):
        if self.model is None:
            yield "I'm sorry, I'm having trouble right now. Please try again later."
            return

        try:
            stream = self.model.create_chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": question},
                ],
                max_tokens=GEN_MAX_NEW_TOKENS,
                temperature=GEN_TEMPERATURE,
                top_p=GEN_TOP_P,
                stop=["<|im_end|>", "<|endoftext|>"],
                stream=True,
            )
            for chunk in stream:
                delta = chunk['choices'][0].get('delta', {})
                content = delta.get('content', '')
                if content:
                    yield content
        except Exception as e:
            logger.error("❌ [LLM] Stream error: %s", e, exc_info=True)
            yield "I'm sorry, I'm having trouble right now. Please try again later."


# ------------------------------------------------------------------------------
# RAG Chain
# ------------------------------------------------------------------------------
class RAGChain:
    def __init__(self, retriever_obj: BaseRetriever, llm: QwenChatModel):
        self.retriever = retriever_obj
        self.llm = llm

    def invoke(self, question: str) -> str:
        pack = retrieve_with_scores(question, k=RETRIEVAL_K_DEFAULT)
        docs = pack["docs"]
        score_type = pack["score_type"]
        scores = pack["scores"]

        context = "\n".join([d.page_content for d in docs]) if docs else ""

        # Use RAG prompt if we have relevant context, otherwise general counselor
        if context.strip() and retrieval_is_relevant(score_type, scores, docs=docs):
            system = RAG_SYSTEM_PROMPT.format(context=context)
            logger.info("✅ [RAG] Using retrieved context (%d docs, score_type=%s)", len(docs), score_type)
        else:
            system = SYSTEM_PROMPT
            logger.info("ℹ️ [RAG] No relevant docs found — using general counselor mode.")

        return self.llm.generate(question, system_prompt=system)

    def stream(self, question: str):
        pack = retrieve_with_scores(question, k=RETRIEVAL_K_DEFAULT)
        docs = pack["docs"]
        score_type = pack["score_type"]
        scores = pack["scores"]

        context = "\n".join([d.page_content for d in docs]) if docs else ""

        if context.strip() and retrieval_is_relevant(score_type, scores, docs=docs):
            system = RAG_SYSTEM_PROMPT.format(context=context)
            logger.info("✅ [RAG] Streaming with retrieved context (%d docs)", len(docs))
        else:
            system = SYSTEM_PROMPT
            logger.info("ℹ️ [RAG] Streaming in general counselor mode.")

        yield from self.llm.stream(question, system_prompt=system)


# ------------------------------------------------------------------------------
# Sources helper
# ------------------------------------------------------------------------------
def get_sources(question: str, k: int = RETRIEVAL_K_DEFAULT) -> List[Dict[str, Any]]:
    pack = retrieve_with_scores(question, k=k)
    docs = pack["docs"]
    score_type = pack["score_type"]
    scores = pack["scores"]

    if not docs or not retrieval_is_relevant(score_type, scores, docs=docs):
        return []

    items: List[Dict[str, Any]] = []
    for i, d in enumerate(docs):
        s = scores[i] if i < len(scores) else None
        items.append({
            "id": i + 1,
            "rank": i + 1,
            "source": d.metadata.get("source", "unknown"),
            "preview": (d.page_content or "")[:160],
            "score_type": score_type,
            "score": None if s is None else float(s),
        })
    return items


# ------------------------------------------------------------------------------
# Build / Init
# ------------------------------------------------------------------------------
def build_rag_chain() -> Tuple[RAGChain, BaseRetriever]:
    global vectorstore
    logger.info("🛠️ [RAG] Building components (Embeddings + VectorStore + Retriever + LLM)...")

    embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
    vectorstore = _build_vectorstore(embeddings)
    retriever_obj = vectorstore.as_retriever(search_kwargs={"k": RETRIEVAL_K_DEFAULT})

    llm = QwenChatModel(model_path=GGUF_MODEL_PATH)
    return RAGChain(retriever_obj, llm), retriever_obj


def reindex_all() -> Tuple[RAGChain, BaseRetriever]:
    if os.path.exists(CHROMA_DIR):
        shutil.rmtree(CHROMA_DIR)
    return build_rag_chain()


def smoke_test_generation() -> Optional[str]:
    if rag_chain is None or rag_chain.llm is None or rag_chain.llm.model is None:
        return "smoke_test: model object is missing"
    out = rag_chain.llm.generate("Hello, how are you?")
    if not out or out.startswith("Error:"):
        return f"smoke_test: {out}"
    logger.info("✅ [Smoke] Response: %s", out[:100])
    return None


def initialize_global_vars(force: bool = False) -> ServiceState:
    global rag_chain, retriever

    if state.initialized and not force:
        logger.info("ℹ️ [System] RAG already initialized; skipping.")
        return state

    state.initialized = False
    state.model_loaded = False
    state.init_error = None

    try:
        logger.info("🌟 [System] Starting Global RAG Initialization...")
        rag_chain, retriever = build_rag_chain()

        state.initialized = True
        state.model_loaded = bool(rag_chain and rag_chain.llm and rag_chain.llm.model)

        if not state.model_loaded:
            state.init_error = "No usable LLM model loaded."
            logger.error("⚠️ [System] %s", state.init_error)
            return state

        err = smoke_test_generation()
        if err is None:
            state.init_error = None
            logger.info("✅ [System] Smoke test passed. Teen Zen ready! 🧘")
        else:
            state.init_error = err
            logger.warning("⚠️ [System] Smoke test warning: %s", err)

    except Exception as e:
        state.initialized = True
        state.model_loaded = False
        state.init_error = str(e)
        logger.critical("💥 [System] Global initialization failed.", exc_info=True)

    return state