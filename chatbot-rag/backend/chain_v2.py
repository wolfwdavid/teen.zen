# chain_v2.py
import os
import shutil
import logging
from typing import Tuple, Optional, List, Dict, Any

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document

from transformers import AutoTokenizer
from optimum.onnxruntime import ORTModelForCausalLM
import torch  # CPU tensors for ONNX model

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

RAG_PROMPT_TEMPLATE = """
You are a concise, helpful expert. Use ONLY the context below to answer.
- Do NOT repeat the user's question.
- Do NOT include banners, disclaimers, or system notes.
- Answer in clear paragraphs.

Context:
{context}

User question: {question}
Answer:
"""

DOCS_DIR = os.getenv("DOCS_DIR", "./docs")
CHROMA_DIR = os.getenv("CHROMA_DIR", "./.chroma")
CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "rag-index")

EMBED_MODEL = os.getenv("EMBED_MODEL", "BAAI/bge-small-en-v1.5")
EMBED_DEVICE = os.getenv("EMBED_DEVICE", "").strip().lower()  # "cpu" or "cuda"

LOCAL_ONNX_MODEL_DIR = os.getenv("LOCAL_ONNX_MODEL_DIR", "./models/local-onnx-model")

ORT_PROVIDERS_ENV = os.getenv("ORT_PROVIDERS", "")
if ORT_PROVIDERS_ENV:
    ORT_PROVIDERS = [p.strip() for p in ORT_PROVIDERS_ENV.split(",") if p.strip()]
else:
    ORT_PROVIDERS = ["CPUExecutionProvider"]

MAX_NEW_TOKENS = int(os.getenv("MAX_NEW_TOKENS", "120"))
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "800"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "80"))


def _pick_embed_device() -> str:
    if EMBED_DEVICE in {"cpu", "cuda"}:
        return EMBED_DEVICE
    try:
        import torch as _torch  # noqa
        return "cuda" if _torch.cuda.is_available() else "cpu"
    except Exception:
        return "cpu"


def _load_documents(docs_dir: str) -> List[Document]:
    if not os.path.isdir(docs_dir):
        raise FileNotFoundError(
            f"Directory not found: '{docs_dir}'. Create it and add .txt/.md files."
        )

    loaders = [
        DirectoryLoader(docs_dir, glob="**/*.txt", loader_cls=TextLoader, show_progress=True),
        DirectoryLoader(docs_dir, glob="**/*.md", loader_cls=TextLoader, show_progress=True),
    ]

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )

    all_docs: List[Document] = []
    for ld in loaders:
        docs = ld.load()
        for d in docs:
            d.metadata = d.metadata or {}
            d.metadata.setdefault("source", d.metadata.get("source") or "unknown")
        if docs:
            all_docs.extend(splitter.split_documents(docs))

    if not all_docs:
        raise RuntimeError(
            f"No documents were found/split under '{docs_dir}'. "
            "Add at least one .txt or .md file."
        )

    logger.info("Loaded %d chunks from '%s'", len(all_docs), docs_dir)
    return all_docs


def _has_persist(path: str) -> bool:
    return os.path.isdir(path) and any(True for _ in os.scandir(path))


def _build_vectorstore(embeddings: HuggingFaceEmbeddings) -> Chroma:
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


class OnnxChatModel:
    def __init__(self, model_dir: str, providers: Optional[list] = None):
        if not os.path.isdir(model_dir):
            raise FileNotFoundError(
                f"LOCAL_ONNX_MODEL_DIR='{model_dir}' does not exist. "
                f"Place a converted ONNX model there or update the env var."
            )

        providers = providers or ["CPUExecutionProvider"]
        logger.info("Loading ONNX model from '%s' with providers=%s", model_dir, providers)

        self.tokenizer = AutoTokenizer.from_pretrained(model_dir)
        self.model = ORTModelForCausalLM.from_pretrained(
            model_dir,
            provider=providers[0],
            provider_options=None,
        )

    def generate(self, prompt: str, max_new_tokens: int = MAX_NEW_TOKENS) -> str:
        inputs = self.tokenizer(prompt, return_tensors="pt")
        input_ids = inputs["input_ids"]

        with torch.no_grad():
            gen_ids = self.model.generate(
                input_ids,
                max_new_tokens=max_new_tokens,
                do_sample=False,
            )

        generated = gen_ids[0, input_ids.shape[1]:]
        text = self.tokenizer.decode(generated, skip_special_tokens=True)
        return text.strip()

    def stream(self, prompt: str, max_new_tokens: int = MAX_NEW_TOKENS, chunk_size: int = 8):
        full = self.generate(prompt, max_new_tokens=max_new_tokens)
        if not full:
            return
        words = full.split(" ")
        chunk: List[str] = []
        for w in words:
            chunk.append(w)
            if len(chunk) >= chunk_size:
                yield " ".join(chunk) + " "
                chunk = []
        if chunk:
            yield " ".join(chunk) + " "


def _format_context(docs: List[Document]) -> str:
    parts = []
    for d in docs:
        src = d.metadata.get("source", "unknown")
        parts.append(f"[{src}]\n{d.page_content}")
    return "\n\n---\n\n".join(parts)


def get_sources(question: str, retriever_obj) -> List[Dict[str, Any]]:
    docs: List[Document] = retriever_obj.get_relevant_documents(question)  # type: ignore[attr-defined]
    items = []
    for idx, d in enumerate(docs):
        meta = d.metadata or {}
        src = meta.get("source", "unknown")

        href = None
        try:
            if os.path.isabs(src):
                rel = os.path.relpath(src, DOCS_DIR)
            else:
                rel = src
            href = f"/docs/{rel}".replace("\\", "/")
        except Exception:
            href = None

        preview = (d.page_content or "").strip().replace("\n", " ")
        if len(preview) > 160:
            preview = preview[:157] + "..."

        items.append(
            {
                "id": idx + 1,
                "source": src,
                "href": href,
                "preview": preview,
            }
        )
    return items


class RAGOnnxChain:
    def __init__(self, retriever_obj, llm: OnnxChatModel):
        self.retriever = retriever_obj
        self.llm = llm

    def _build_prompt(self, question: str) -> str:
        docs: List[Document] = self.retriever.get_relevant_documents(question)  # type: ignore[attr-defined]
        ctx = _format_context(docs)
        prompt = RAG_PROMPT_TEMPLATE.format(context=ctx, question=question)
        return prompt

    def invoke(self, question: str) -> str:
        prompt = self._build_prompt(question)
        return self.llm.generate(prompt, max_new_tokens=MAX_NEW_TOKENS)

    def stream(self, question: str):
        prompt = self._build_prompt(question)
        for chunk in self.llm.stream(prompt, max_new_tokens=MAX_NEW_TOKENS):
            yield chunk


def build_rag_chain() -> Tuple[RAGOnnxChain, object]:
    device = _pick_embed_device()
    logger.info("Using embeddings model '%s' on device '%s'", EMBED_MODEL, device)

    embeddings = HuggingFaceEmbeddings(
        model_name=EMBED_MODEL,
        model_kwargs={"device": device},
        encode_kwargs={"normalize_embeddings": True},
    )

    vectorstore = _build_vectorstore(embeddings)

    retriever_obj = vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs={"k": 4, "fetch_k": 12, "lambda_mult": 0.5},
    )

    llm = OnnxChatModel(model_dir=LOCAL_ONNX_MODEL_DIR, providers=ORT_PROVIDERS)
    rag_chain = RAGOnnxChain(retriever_obj=retriever_obj, llm=llm)
    return rag_chain, retriever_obj


def reindex_all() -> Tuple[RAGOnnxChain, object]:
    if os.path.isdir(CHROMA_DIR):
        logger.info("Deleting Chroma dir '%s' for full reindex ...", CHROMA_DIR)
        shutil.rmtree(CHROMA_DIR, ignore_errors=True)
    return build_rag_chain()


rag_chain: Optional[RAGOnnxChain] = None
retriever: Optional[object] = None

if os.getenv("EAGER_BUILD", "").lower() in {"1", "true", "yes"}:
    rag_chain, retriever = build_rag_chain()
