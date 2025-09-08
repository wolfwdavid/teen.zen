import logging
from langchain_community.document_loaders import DirectoryLoader 
from langchain_community.embeddings import HuggingFaceBgeEmbeddings
from langchain_community.llms import HuggingFaceTextGenInference
from langchain.prompts import PromptTemplate
from langchain.schema.runnable import RunnablePassthrough
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma

logging.basicConfig(level=logging.INFO)

RAG_PROMPT_TEMPLATE = """
Here is context from documents that may be useful:
{context}

Answer the question as a helpful expert. Use only the context above.
User: {question}
Assistant:
"""

loader = DirectoryLoader("./docs")
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1024, chunk_overlap=128)
docs = loader.load_and_split(text_splitter)

hf = HuggingFaceBgeEmbeddings(
    model_name="BAAI/bge-large-en-v1.5",
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True}
)

vectorstore = Chroma.from_documents(docs, hf)
retriever = vectorstore.as_retriever()

llm = HuggingFaceTextGenInference(
    inference_server_url="http://0.0.0.0:8080/",
    max_new_tokens=512,
    temperature=0.5,
    repetition_penalty=1.03,
    streaming=True,
)

rag_prompt = PromptTemplate.from_template(RAG_PROMPT_TEMPLATE)
rag_chain = {"context": retriever, "question": RunnablePassthrough()} | rag_prompt | llm
