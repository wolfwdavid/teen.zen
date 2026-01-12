import os
import logging
from pathlib import Path
from functools import lru_cache

# --- External Libraries ---
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.llms import VLLM
from langchain_core.prompts import PromptTemplate
from langchain.chains import RetrievalQA
from langchain_core.runnables import RunnableParallel, RunnablePassthrough, RunnableLambda
from optimum.onnxruntime import ORTModelForCausalLM
from transformers import AutoTokenizer, GenerationConfig

# Disable ChromaDB telemetry errors
os.environ["CHROMA_SERVER_NO_TELEMETRY"] = "true"

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configuration ---

# 1. Path Fix: Use pathlib to resolve the model directory ABSOLUTELY.
# This makes the LOCAL_ONNX_MODEL_DIR environment variable UNNECESSARY.
BASE_DIR = Path(__file__).parent.resolve()
LOCAL_ONNX_MODEL_PATH = BASE_DIR / "models" / "local-onnx-model"
LOCAL_ONNX_MODEL_DIR = str(LOCAL_ONNX_MODEL_PATH)

# Fallback for LLM Providers (should be set in env, but defaults to CPU)
ORT_PROVIDERS = os.environ.get("ORT_PROVIDERS", "CPUExecutionProvider").split(",")

# Fallback for Token Limits
MAX_NEW_TOKENS = int(os.environ.get("MAX_NEW_TOKENS", 120))


# --- Custom ONNX Model Class ---

class OnnxChatModel:
    """A wrapper for the ONNX Causal Language Model."""

    def __init__(self, model_dir: str, providers: list):
        logger.info(f"Loading ONNX model from '{model_dir}' with providers={providers}")

        # Note: from_pretrained loads model.onnx and model.onnx_data, etc.
        # This will now use the guaranteed absolute path from LOCAL_ONNX_MODEL_DIR
        self.model = ORTModelForCausalLM.from_pretrained(
            model_dir,
            provider=providers,
            export=False, # Model is already exported
        )
        self.tokenizer = AutoTokenizer.from_pretrained(model_dir)
        self.generation_config = GenerationConfig.from_pretrained(model_dir)
        self.generation_config.max_new_tokens = MAX_NEW_TOKENS

        # Set default provider (important for ORT)
        if len(providers) > 0:
            self.model.providers = providers


    def generate(self, prompt: str) -> str:
        """Generates text from a prompt."""
        # The prompt is already the fully constructed RAG prompt (context + question)

        # 1. Tokenize the input prompt
        input_ids = self.tokenizer.encode(
            prompt, 
            return_tensors="pt", 
            return_token_type_ids=False
        )

        # 2. Generate the response
        generated_ids = self.model.generate(
            input_ids, 
            generation_config=self.generation_config
        )

        # 3. Decode the generated tokens
        # Decode the output, skipping the prompt tokens and special tokens
        generated_text = self.tokenizer.decode(
            generated_ids[0, input_ids.shape[-1]:], 
            skip_special_tokens=True
        )

        return generated_text


# --- RAG Chain Construction ---

# Cache the embeddings model, as it's large and slow to load
@lru_cache(maxsize=1)
def get_embeddings_model():
    """Load the BAAI/bge-small-en-v1.5 embeddings model."""
    logger.info(f"Using embeddings model 'BAAI/bge-small-en-v1.5' on device 'cpu'")
    # We must explicitly use the CPU as the environment is not set up for GPU
    embeddings = HuggingFaceEmbeddings(
        model_name="BAAI/bge-small-en-v1.5",
        model_kwargs={'device': 'cpu'},
        # The ChromaDB index needs the normalize_embeddings=True setting
        encode_kwargs={'normalize_embeddings': True}, 
    )
    return embeddings

@lru_cache(maxsize=1)
def get_vector_store():
    """Load the Chroma vector store."""
    embeddings = get_embeddings_model()
    chroma_path = str(BASE_DIR / ".chroma")
    collection_name = "rag-index"

    logger.info(f"Loading existing Chroma DB from '{chroma_path}' (collection='{collection_name}') ...")
    
    # Load the existing database
    # Note: Chroma uses the embeddings model to check for compatibility
    return Chroma(
        persist_directory=chroma_path,
        embedding_function=embeddings,
        collection_name=collection_name
    )

def format_docs(docs):
    """Formats the documents for inclusion in the prompt."""
    formatted_docs = []
    # Include source file name (path) in the context
    for i, doc in enumerate(docs):
        source_path = doc.metadata.get('source', 'Unknown Source')
        # Clean up the source path for display (e.g., just show docs/intro.txt)
        cleaned_source = '/'.join(source_path.split(os.path.sep)[-2:])
        
        formatted_docs.append(
            f"Context [{cleaned_source}]: {doc.page_content}"
        )
    return "\n\n".join(formatted_docs)

# Template for the Prompt
RAG_PROMPT_TEMPLATE = """
You are a helpful and harmless assistant. Your task is to answer the question based
ONLY on the provided context. If the answer is not found in the context, politely state 
that the information is not available in the current knowledge base.

Context:
{context}

Question: {question}
Answer:"""
RAG_PROMPT = PromptTemplate.from_template(RAG_PROMPT_TEMPLATE)


def build_rag_chain():
    """Builds and returns the complete RAG chain and the retriever."""
    logger.info("Building chain + retriever...")
    
    # 1. Initialize the Retriever (the search engine for the context)
    vectorstore = get_vector_store()
    # Use a high k for more context, but this can be tuned
    retriever = vectorstore.as_retriever(search_kwargs={"k": 5})

    # 2. Initialize the LLM (the model that generates the final answer)
    # The model directory is now guaranteed to be absolute and correct
    llm = OnnxChatModel(model_dir=LOCAL_ONNX_MODEL_DIR, providers=ORT_PROVIDERS)
    
    # Helper to invoke the LLM
    def llm_invoke(prompt):
        return llm.generate(prompt)

    # 3. Assemble the RAG Chain using LangChain Expression Language (LCEL)
    rag_chain = (
        # A. Search for context documents based on the user question
        RunnableParallel(
            # Run the retriever in parallel with the user question (passthrough)
            context=retriever | format_docs, 
            question=RunnablePassthrough(),
            source_docs=retriever # Save docs for citation
        )
        # B. Plug context and question into the prompt template
        | RAG_PROMPT
        # C. Pass the final prompt to the LLM for generation
        | RunnableLambda(llm_invoke)
    )

    logger.info("RAG Chain initialization complete.")
    return rag_chain, retriever

if __name__ == '__main__':
    # Simple test run (will fail without Uvicorn context, but useful for quick debug)
    print("Testing chain initialization...")
    try:
        rag_chain, _ = build_rag_chain()
        print("Chain built successfully.")
    except Exception as e:
        print(f"Failed to build chain: {e}")