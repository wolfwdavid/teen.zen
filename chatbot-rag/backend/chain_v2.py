import os
import shutil
import logging
import time
import warnings
import re
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
# PATCHED: Using sentence_transformers directly to avoid compatibility issues
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
warnings.filterwarnings("ignore", message=".*TracerWarning.*")
warnings.filterwarnings("ignore", message=".*torch_dtype.*")

# BitNet native (optional)
try:
    from bitnet import BitNetInference  # type: ignore
    BITNET_AVAILABLE = True
except Exception:
    BITNET_AVAILABLE = False

# HF / ORT
from transformers import AutoTokenizer, AutoModelForCausalLM  # type: ignore

try:
    import sentencepiece  # noqa: F401
    from transformers import LlamaTokenizer  # type: ignore
    SENTENCEPIECE_AVAILABLE = True
except Exception:
    LlamaTokenizer = None  # type: ignore
    SENTENCEPIECE_AVAILABLE = False

try:
    from transformers import GPT2TokenizerFast  # type: ignore
    GPT2_FAST_AVAILABLE = True
except Exception:
    GPT2TokenizerFast = None  # type: ignore
    GPT2_FAST_AVAILABLE = False

from optimum.onnxruntime import ORTModelForCausalLM  # type: ignore

# ------------------------------------------------------------------------------
# Config
# ------------------------------------------------------------------------------
RAG_PROMPT_TEMPLATE = """You are a retrieval QA assistant.

RULES:
- Use ONLY the Context.
- If the Context does not contain the answer, say: "I don't know."
- Keep the answer to 1-3 short sentences.
- Do not ask the user questions.

Context:
{context}

Question: {question}

Answer:"""

DOCS_DIR = os.getenv("DOCS_DIR", "./docs")
CHROMA_DIR = os.getenv("CHROMA_DIR", "./.chroma")
CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "rag-index")
EMBED_MODEL = os.getenv("EMBED_MODEL", "BAAI/bge-small-en-v1.5")

# Primary model (BitNet)
BITNET_MODEL_PATH = os.getenv("BITNET_MODEL_PATH", "1bitLLM/bitnet_b1_58-large")

# Export ONNX only when explicitly requested
BITNET_ONNX_EXPORT = os.getenv("BITNET_ONNX_EXPORT", "0") == "1"

# Local ONNX cache path
ONNX_DIR = os.getenv("ONNX_DIR", "./.onnx")
MODEL_SLUG = BITNET_MODEL_PATH.split("/")[-1].replace(":", "_")
LOCAL_ONNX_PATH = os.path.join(ONNX_DIR, MODEL_SLUG)

# Fallback model
FALLBACK_MODEL_PATH = os.getenv("FALLBACK_MODEL_PATH", "distilgpt2")

# ------------------------------------------------------------------------------
# Generation tuning (deterministic by default for RAG)
# ------------------------------------------------------------------------------
GEN_MAX_NEW_TOKENS = int(os.getenv("GEN_MAX_NEW_TOKENS", "96"))
GEN_DO_SAMPLE = os.getenv("GEN_DO_SAMPLE", "0") == "1"
GEN_TEMPERATURE = float(os.getenv("GEN_TEMPERATURE", "0.0" if not GEN_DO_SAMPLE else "0.7"))
GEN_TOP_P = float(os.getenv("GEN_TOP_P", "1.0" if not GEN_DO_SAMPLE else "0.9"))
GEN_REP_PENALTY = float(os.getenv("GEN_REP_PENALTY", "1.10"))

# ------------------------------------------------------------------------------
# Retrieval scoring + gating
# ------------------------------------------------------------------------------
RETRIEVAL_K_DEFAULT = int(os.getenv("RETRIEVAL_K", "3"))

# If we have normalized relevance scores (0..1, higher better)
MIN_RELEVANCE_SCORE = float(os.getenv("MIN_RELEVANCE_SCORE", "0.20"))

# If we only have "distance" scores (lower better)
MAX_DISTANCE_SCORE = float(os.getenv("MAX_DISTANCE_SCORE", "1.25"))

# ------------------------------------------------------------------------------
# Global readiness state
# ------------------------------------------------------------------------------
@dataclass
class ServiceState:
    initialized: bool = False
    model_loaded: bool = False
    init_error: Optional[str] = None


state = ServiceState()

rag_chain: Optional["RAGBitNetChain"] = None
retriever: Optional[BaseRetriever] = None

# keep vectorstore around so we can fetch scores
vectorstore: Optional[Chroma] = None

# ------------------------------------------------------------------------------
# Debug prints (helps confirm correct file/dirs are being used)
# ------------------------------------------------------------------------------
try:
    print("CHAIN_V2 PATH =", os.path.abspath(__file__), flush=True)
except Exception:
    pass
print("DOCS_DIR =", os.path.abspath(DOCS_DIR), flush=True)
print("CHROMA_DIR =", os.path.abspath(CHROMA_DIR), flush=True)

# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------
def _load_documents(docs_dir: str) -> List[Document]:
    """
    Load docs from DOCS_DIR. If none exist, return [] (do NOT create a fake doc).
    """
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
        logger.warning("⚠️ No documents found in DOCS_DIR=%s (txt/md). RAG will answer 'I don't know.'", docs_dir)
        return []

    return all_docs


def _build_vectorstore(embeddings: HuggingFaceEmbeddings) -> Chroma:
    # Load persisted if it exists
    if os.path.isdir(CHROMA_DIR) and any(os.scandir(CHROMA_DIR)):
        logger.info("📚 [Chroma] Loading persisted index at: %s", CHROMA_DIR)
        return Chroma(
            persist_directory=CHROMA_DIR,
            collection_name=CHROMA_COLLECTION,
            embedding_function=embeddings,
        )

    # Build new
    logger.info("📚 [Chroma] Building new index from docs at: %s", DOCS_DIR)
    docs = _load_documents(DOCS_DIR)

    # If no docs, create an empty collection (clean behavior)
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
        docs,
        embeddings,
        persist_directory=CHROMA_DIR,
        collection_name=CHROMA_COLLECTION,
    )
    try:
        vs.persist()
    except Exception:
        pass
    return vs


def _local_onnx_present(path: str) -> bool:
    if not os.path.isdir(path):
        return False
    try:
        for fn in os.listdir(path):
            if fn.endswith(".onnx") or fn == "model.onnx":
                return True
    except Exception:
        return False
    return False


def _looks_like_gibberish(text: str) -> bool:
    t = (text or "").strip()
    if len(t) < 12:
        return True
    if "�" in t:
        return True

    non_ascii = sum(1 for c in t if ord(c) > 127)
    if non_ascii / max(1, len(t)) > 0.08:
        return True

    punct = sum(1 for c in t if c in ".,;:!?()[]{}<>_/\\|@#$%^&*+=~`")
    if punct / max(1, len(t)) > 0.25:
        return True

    letters = sum(1 for c in t if c.isalpha())
    if letters / max(1, len(t)) < 0.50:
        return True

    vowels = sum(1 for c in t.lower() if c in "aeiou")
    if vowels / max(1, letters) < 0.22:
        return True

    tokens = t.split()
    if len(tokens) >= 8:
        short = sum(1 for w in tokens if len(w.strip(".,;:!?()[]{}")) <= 2)
        if short / len(tokens) > 0.35:
            return True
        abbr = len(re.findall(r"\b\w{1,4}\.\b", t))
        if abbr >= 4:
            return True
        uniq = len(set(tokens))
        if uniq / len(tokens) < 0.55:
            return True

    return False


def _finalize_answer(text: str) -> str:
    t = (text or "").strip()

    if "Answer:" in t:
        t = t.split("Answer:", 1)[-1].strip()

    if "\n" in t:
        t = t.split("\n", 1)[0].strip()

    for bad in ["RULES:", "Context:", "Question:"]:
        if bad in t:
            t = t.split(bad, 1)[0].strip()

    t = t.strip(" \t\r\n\"'")
    return t or "I don't know."


# ------------------------------------------------------------------------------
# Scored retrieval (visibility + gating)
# ------------------------------------------------------------------------------
def retrieve_with_scores(question: str, k: int = RETRIEVAL_K_DEFAULT) -> Dict[str, Any]:
    """
    Returns:
      {
        "docs": [Document...],
        "score_type": "relevance" | "distance" | "none",
        "scores": [float...]  # aligned with docs
      }
    """
    if vectorstore is None:
        return {"docs": [], "score_type": "none", "scores": []}

    # Prefer normalized relevance scores (0..1, higher better)
    if hasattr(vectorstore, "similarity_search_with_relevance_scores"):
        try:
            pairs = vectorstore.similarity_search_with_relevance_scores(question, k=k)
            docs = [d for d, _ in pairs]
            scores = [float(s) for _, s in pairs]
            return {"docs": docs, "score_type": "relevance", "scores": scores}
        except Exception as e:
            logger.warning("⚠️ [Retrieval] relevance_scores failed; falling back. err=%s", e)

    # Fallback: distance-like scores (lower better)
    if hasattr(vectorstore, "similarity_search_with_score"):
        try:
            pairs = vectorstore.similarity_search_with_score(question, k=k)
            docs = [d for d, _ in pairs]
            scores = [float(s) for _, s in pairs]
            return {"docs": docs, "score_type": "distance", "scores": scores}
        except Exception as e:
            logger.warning("⚠️ [Retrieval] with_score failed. err=%s", e)

    # Last fallback: docs only (no scores)
    try:
        docs = vectorstore.similarity_search(question, k=k)  # type: ignore
        return {"docs": docs, "score_type": "none", "scores": [None] * len(docs)}
    except Exception:
        return {"docs": [], "score_type": "none", "scores": []}


def retrieval_is_relevant(score_type: str, scores: List[Any], docs: Optional[List[Document]] = None) -> bool:
    """
    Decide if retrieval is good enough to answer.
    Conservative defaults: if we can't score, require real non-trivial content.
    """
    docs = docs or []
    if not docs:
        return False

    # If we don't have real scores, require some non-trivial context
    if score_type == "none" or not scores:
        joined = "\n".join([d.page_content.strip() for d in docs if d.page_content])
        return len(joined.strip()) >= 40  # small but non-empty threshold

    if score_type == "relevance":
        try:
            top = float(scores[0])
            return top >= MIN_RELEVANCE_SCORE
        except Exception:
            return False

    if score_type == "distance":
        try:
            top = float(scores[0])
            return top <= MAX_DISTANCE_SCORE
        except Exception:
            return False

    return False


# ------------------------------------------------------------------------------
# Model wrapper
# ------------------------------------------------------------------------------
class DualChatModel:
    def __init__(self, bitnet_path: str, fallback_path: str):
        self.bitnet = BitNetChatModel(bitnet_path)
        self.fallback = HFChatModel(fallback_path)

        if self.bitnet.model is not None:
            logger.info("✅ [LLM] BitNet primary model loaded.")
        else:
            logger.warning("⚠️ [LLM] BitNet primary failed: %s", self.bitnet.last_error)

        if self.fallback.model is not None:
            logger.info("✅ [LLM] Fallback model loaded: %s", fallback_path)
        else:
            logger.error("❌ [LLM] Fallback model failed to load. %s", self.fallback.last_error)

    @property
    def model(self):
        return self.fallback.model or self.bitnet.model

    def generate(self, prompt: str) -> str:
        if self.bitnet.model is not None:
            out = self.bitnet.generate(prompt)
            out2 = _finalize_answer(out)

            if out2.startswith("Error:"):
                logger.warning("⚠️ [LLM] BitNet errored; using fallback. err=%s", out2)
            elif _looks_like_gibberish(out2):
                logger.warning("⚠️ [LLM] BitNet gibberish; using fallback. sample=%r", out2[:120])
            else:
                logger.info("✅ [LLM] Answered with BitNet.")
                return out2

        fb = self.fallback.generate(prompt)
        fb2 = _finalize_answer(fb)
        logger.info("✅ [LLM] Answered with FALLBACK. model=%s", FALLBACK_MODEL_PATH)
        return fb2

    def stream(self, prompt: str):
        text = self.generate(prompt)
        if text.startswith("Error:"):
            yield text
            return
        for w in text.split():
            yield w + " "
            time.sleep(0.01)


class HFChatModel:
    def __init__(self, model_path: str):
        self.model = None
        self.tokenizer = None
        self.last_error: Optional[str] = None

        try:
            logger.info("📦 [Fallback] Loading HF model: %s", model_path)
            self.tokenizer = AutoTokenizer.from_pretrained(model_path, use_fast=True)
            if getattr(self.tokenizer, "pad_token", None) is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            self.model = AutoModelForCausalLM.from_pretrained(model_path)
            logger.info("✅ [Fallback] HF model ready.")
        except Exception as e:
            self.last_error = str(e)
            logger.critical("❌ [Fallback] Failed to load HF fallback model.", exc_info=True)
            self.model = None
            self.tokenizer = None

    def generate(self, prompt: str) -> str:
        if self.model is None or self.tokenizer is None:
            return f"Error: Fallback model not loaded. {self.last_error or ''}".strip()

        inputs = self.tokenizer(prompt, return_tensors="pt")
        gen_ids = self.model.generate(
            **inputs,
            max_new_tokens=GEN_MAX_NEW_TOKENS,
            do_sample=GEN_DO_SAMPLE,
            temperature=GEN_TEMPERATURE,
            top_p=GEN_TOP_P,
            repetition_penalty=GEN_REP_PENALTY,
            eos_token_id=self.tokenizer.eos_token_id,
            pad_token_id=self.tokenizer.eos_token_id,
        )
        input_len = inputs["input_ids"].shape[-1]
        new_tokens = gen_ids[0][input_len:]
        return self.tokenizer.decode(new_tokens, skip_special_tokens=True).strip()


class BitNetChatModel:
    def __init__(self, model_path: str):
        self.model = None
        self.tokenizer = None
        self.is_bitnet_native = False
        self.last_error: Optional[str] = None

        if BITNET_AVAILABLE:
            try:
                logger.info("🚀 [BitNet] Attempting Native Load: %s", model_path)
                self.model = BitNetInference(model_path)
                self.is_bitnet_native = True
                logger.info("✅ [BitNet] Native Loaded Successfully.")
                return
            except Exception as e:
                self.last_error = str(e)
                logger.warning("⚠️ [BitNet] Native load failed. Falling back. Error: %s", e)

        try:
            logger.info("📦 [BitNet] Initializing ORT fallback for %s...", model_path)

            os.makedirs(LOCAL_ONNX_PATH, exist_ok=True)
            has_onnx = _local_onnx_present(LOCAL_ONNX_PATH)
            logger.info("🧠 [ONNX] local_path=%s present=%s export=%s", LOCAL_ONNX_PATH, has_onnx, BITNET_ONNX_EXPORT)

            if not has_onnx:
                if not BITNET_ONNX_EXPORT:
                    raise RuntimeError(
                        f"No local ONNX files found at '{LOCAL_ONNX_PATH}'. "
                        f"Run ONCE with BITNET_ONNX_EXPORT=1 to export & save the ONNX model."
                    )
                logger.warning("⚙️ [ONNX] Exporting model to local cache: %s (one-time)", LOCAL_ONNX_PATH)
                model = ORTModelForCausalLM.from_pretrained(model_path, export=True, trust_remote_code=True)
                model.save_pretrained(LOCAL_ONNX_PATH)
                self.model = model
                logger.info("✅ [ONNX] Export complete and saved.")
            else:
                self.model = ORTModelForCausalLM.from_pretrained(LOCAL_ONNX_PATH, export=False, trust_remote_code=True)

            self.tokenizer = self._load_tokenizer_prefer_local(model_path, LOCAL_ONNX_PATH)
            if self.tokenizer is None:
                raise RuntimeError("Tokenizer could not be loaded for BitNet ORT model.")

            if getattr(self.tokenizer, "pad_token", None) is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token

            logger.info("✅ [BitNet] ORT model ready.")
        except Exception as e:
            self.last_error = str(e)
            logger.critical("❌ [BitNet] CRITICAL: All model loading paths failed.", exc_info=True)
            self.model = None
            self.tokenizer = None
            self.is_bitnet_native = False

    def _load_tokenizer_prefer_local(self, remote_path: str, local_path: str):
        try:
            tok = AutoTokenizer.from_pretrained(local_path, trust_remote_code=True)
            logger.info("✅ [Tokenizer] Loaded from LOCAL_ONNX_PATH.")
            return tok
        except Exception:
            pass

        try:
            tok = AutoTokenizer.from_pretrained(remote_path, trust_remote_code=True)
            logger.info("✅ [Tokenizer] Loaded via AutoTokenizer (trust_remote_code=True).")
            return tok
        except Exception as e:
            logger.warning("⚠️ [Tokenizer] AutoTokenizer(trust_remote_code=True) failed: %s", e)

        try:
            tok = AutoTokenizer.from_pretrained(remote_path, trust_remote_code=False)
            logger.info("✅ [Tokenizer] Loaded via AutoTokenizer (trust_remote_code=False).")
            return tok
        except Exception as e:
            logger.warning("⚠️ [Tokenizer] AutoTokenizer(trust_remote_code=False) failed: %s", e)

        if GPT2_FAST_AVAILABLE:
            try:
                tok = GPT2TokenizerFast.from_pretrained(remote_path)
                logger.info("✅ [Tokenizer] Loaded via GPT2TokenizerFast.")
                return tok
            except Exception as e:
                logger.warning("⚠️ [Tokenizer] GPT2TokenizerFast failed: %s", e)

        if SENTENCEPIECE_AVAILABLE and LlamaTokenizer is not None:
            try:
                tok = LlamaTokenizer.from_pretrained(remote_path)
                logger.info("✅ [Tokenizer] Loaded via LlamaTokenizer.")
                return tok
            except Exception as e:
                logger.warning("⚠️ [Tokenizer] LlamaTokenizer failed: %s", e)

        return None

    def generate(self, prompt: str) -> str:
        if not self.model or not self.tokenizer:
            return f"Error: Model not loaded. {self.last_error or ''}".strip()

        try:
            if self.is_bitnet_native:
                return self.model.generate(prompt, max_new_tokens=GEN_MAX_NEW_TOKENS).strip()

            inputs = self.tokenizer(prompt, return_tensors="pt")
            gen_ids = self.model.generate(
                **inputs,
                max_new_tokens=GEN_MAX_NEW_TOKENS,
                do_sample=GEN_DO_SAMPLE,
                temperature=GEN_TEMPERATURE,
                top_p=GEN_TOP_P,
                repetition_penalty=GEN_REP_PENALTY,
            )
            input_len = inputs["input_ids"].shape[-1]
            new_tokens = gen_ids[0][input_len:]
            return self.tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
        except Exception as e:
            logger.error("Generation error", exc_info=True)
            return f"Error: Generation failed. {e}"


# ------------------------------------------------------------------------------
# RAG Chain
# ------------------------------------------------------------------------------
class RAGBitNetChain:
    def __init__(self, retriever_obj: BaseRetriever, llm: DualChatModel):
        self.retriever = retriever_obj
        self.llm = llm

    def invoke(self, question: str) -> str:
        pack = retrieve_with_scores(question, k=RETRIEVAL_K_DEFAULT)
        docs = pack["docs"]
        score_type = pack["score_type"]
        scores = pack["scores"]

        context = "\n".join([d.page_content for d in docs]) if docs else ""

        if (not context.strip()) or (not retrieval_is_relevant(score_type, scores, docs=docs)):
            return "I don't know."

        prompt = RAG_PROMPT_TEMPLATE.format(context=context, question=question)
        return self.llm.generate(prompt)

    def stream(self, question: str):
        pack = retrieve_with_scores(question, k=RETRIEVAL_K_DEFAULT)
        docs = pack["docs"]
        score_type = pack["score_type"]
        scores = pack["scores"]

        context = "\n".join([d.page_content for d in docs]) if docs else ""

        if (not context.strip()) or (not retrieval_is_relevant(score_type, scores, docs=docs)):
            yield "I don't know."
            return

        prompt = RAG_PROMPT_TEMPLATE.format(context=context, question=question)
        yield from self.llm.stream(prompt)


def get_sources(question: str, k: int = RETRIEVAL_K_DEFAULT) -> List[Dict[str, Any]]:
    """
    Includes: score, score_type, rank
    """
    pack = retrieve_with_scores(question, k=k)
    docs = pack["docs"]
    score_type = pack["score_type"]
    scores = pack["scores"]

    if (not docs) or (not retrieval_is_relevant(score_type, scores, docs=docs)):
        return []

    items: List[Dict[str, Any]] = []
    for i, d in enumerate(docs):
        s = scores[i] if i < len(scores) else None
        items.append(
            {
                "id": i + 1,
                "rank": i + 1,
                "source": d.metadata.get("source", "unknown"),
                "preview": (d.page_content or "")[:160],
                "score_type": score_type,
                "score": None if s is None else float(s),
            }
        )
    return items


def build_rag_chain() -> Tuple[RAGBitNetChain, BaseRetriever]:
    global vectorstore
    logger.info("🛠️ [RAG] Building components (Embeddings + VectorStore + Retriever + LLM)...")

    embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
    vectorstore = _build_vectorstore(embeddings)

    retriever_obj = vectorstore.as_retriever(search_kwargs={"k": RETRIEVAL_K_DEFAULT})

    llm = DualChatModel(bitnet_path=BITNET_MODEL_PATH, fallback_path=FALLBACK_MODEL_PATH)
    return RAGBitNetChain(retriever_obj, llm), retriever_obj


def reindex_all() -> Tuple[RAGBitNetChain, BaseRetriever]:
    if os.path.exists(CHROMA_DIR):
        shutil.rmtree(CHROMA_DIR)
    return build_rag_chain()


def smoke_test_generation() -> Optional[str]:
    if rag_chain is None or rag_chain.llm is None or rag_chain.llm.model is None:
        return "smoke_test: model object is missing"
    out = rag_chain.llm.generate(RAG_PROMPT_TEMPLATE.format(context="Hello world", question="What is this?"))
    if out.startswith("Error:"):
        return f"smoke_test: {out}"
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
            state.init_error = "No usable LLM model loaded (BitNet + fallback failed)."
            logger.error("⚠️ [System] %s", state.init_error)
            return state

        err = smoke_test_generation()
        if err is None:
            state.init_error = None
            logger.info("✅ [System] Smoke test passed. Model ready.")
        else:
            state.init_error = err
            logger.warning("⚠️ [System] Smoke test warning: %s", err)

    except Exception as e:
        state.initialized = True
        state.model_loaded = False
        state.init_error = str(e)
        logger.critical("💥 [System] Global initialization failed.", exc_info=True)

    return state