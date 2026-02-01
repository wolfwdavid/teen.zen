from langchain_core.prompts import ChatPromptTemplate
import os
import logging
from typing import Any, Optional
from pydantic import PrivateAttr
from typing import Optional, List, Tuple, Any, NamedTuple
from langchain_core.runnables import RunnableSerializable
from langchain_core.outputs import LLMResult, Generation

# Setup logging
logger = logging.getLogger(__name__)

# --- 1. DEFINITIONS AND STATES ---
class ServiceState(NamedTuple):
    initialized: bool
    model_loaded: bool
    init_error: Optional[str]

# Global variables that the API will use
rag_chain = None
retriever = None
vectorstore = None  # <--- ADD THIS LINE HERE
state = ServiceState(initialized=False, model_loaded=False, init_error=None)

# --- 2. THE MODEL CLASS ---
class BitNetChatModel(RunnableSerializable):
    model_path: str
    
    # 2. Declare these private fields here
    _model: Any = PrivateAttr(default=None)
    _tokenizer: Any = PrivateAttr(default=None)

    def __init__(self, model_path: str, **kwargs):
        super().__init__(model_path=model_path, **kwargs)
        
        # 3. Now this assignment will work perfectly!
        logger.info(f"🚀 Initializing BitNet model from {model_path}")
        # Insert your actual loading logic here, e.g.:
        # self._model = load_bitnet_model(model_path)
        # self._tokenizer = load_bitnet_tokenizer(model_path)

    def invoke(self, input: Any, config: Optional[dict] = None, **kwargs) -> str:
        # LangChain logic to get text
        prompt_text = input.to_string() if hasattr(input, "to_string") else str(input)
        return self.generate(prompt_text)

    def generate(self, prompt: str) -> str:
        # Use the underscore versions here too
        if not self._model or not self._tokenizer:
            return "Error: Model components not initialized properly."
            
        # ... your actual generation logic ...
        return "Model response text"
# --- 3. HELPER FUNCTIONS ---
def build_rag_chain():
    llm = BitNetChatModel(model_path="./models/bitnet_b1_58-large")
    prompt = ChatPromptTemplate.from_template("{question}")
    
    # This creates a 'Chain' object, not a string
    chain = prompt | llm 
    
    return chain, None

def smoke_test_generation():
    """Quick check to see if the model is actually working."""
    return None # Return None if pass, string error if fail

# --- 4. THE INITIALIZATION FUNCTION (FLUSH LEFT) ---
def initialize_global_vars(force: bool = False) -> ServiceState:
    global rag_chain, retriever, state, vectorstore

    # FIX: Only skip if we are initialized AND the chain actually exists.
    if state.initialized and rag_chain is not None and not force:
        logger.info("ℹ️ [System] RAG already initialized and chain is live; skipping.")
        return state

    try:
        logger.info("🌟 [System] Starting Global RAG Initialization...")
        
        # 1. Run the build function
        new_chain, new_retriever = build_rag_chain()
        
        # 2. IMPORTANT: Verify the build didn't return None
        if new_chain is None:
            raise ValueError("build_rag_chain returned None. Check your LLM loading logic.")

        # 3. Explicitly update the global variables
        rag_chain = new_chain
        retriever = new_retriever
        
        # 4. Update the state object
        state = ServiceState(
            initialized=True, 
            model_loaded=True, 
            init_error=None
        )
        logger.info("✅ [System] Initialization complete. Global RAG chain is now assigned.")

    except Exception as e:
        state = ServiceState(
            initialized=True, 
            model_loaded=False, 
            init_error=str(e)
        )
        logger.critical(f"💥 [System] Global initialization failed: {e}")

    return state