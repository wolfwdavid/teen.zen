import os
import logging
import json
import chain_v2 # The core module
from typing import Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr
from dotenv import load_dotenv

# Import auth logic
from auth import (
    create_user, authenticate_user, create_access_token, 
    generate_verification_code, send_verification_email, verify_code, load_users
)

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('api_v2')

app = FastAPI(title='RAG Chatbot – V2')

# --- INITIALIZATION ---
# This runs once when the script starts to ensure the chain is ready
@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Starting up API server...")
    # This updates the rag_chain inside the chain_v2 module
    chain_v2.initialize_global_vars()
    logger.info("✅ RAG chain initialized and ready for requests.")

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- MODELS ---
class ChatRequest(BaseModel):
    question: str

class SendCodeRequest(BaseModel):
    email: EmailStr

class VerifyCodeRequest(BaseModel):
    email: EmailStr
    code: str

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    role: str = 'user'

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    email: str
    role: str

# --- ENDPOINTS ---

@app.get('/health')
def health():
    """Checks the live state of the module-level variables."""
    return {
        "ok": True,
        "initialized": chain_v2.state.initialized,
        "model_loaded": chain_v2.state.model_loaded,
        "rag_chain_is_none": chain_v2.rag_chain is None,
        "retriever_is_none": chain_v2.retriever is None,
        "vectorstore_is_none": chain_v2.vectorstore is None
    }

@app.post('/api/chat')
async def chat(req: ChatRequest):
    try:
        # Access through the module to see the initialized object
        if chain_v2.rag_chain is None:
            raise HTTPException(status_code=503, detail="RAG system not initialized")
        
        # Invoke the chain
        answer = chain_v2.rag_chain.invoke(req.question)
        return {"answer": answer}
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal chatbot error: {str(e)}")

@app.get('/api/chat/stream')
async def chat_stream(question: str = Query(...)):
    async def event_generator():
        try:
            logger.info(f"🔍 [Stream] Question: {question}")
            
            # Use module-level reference
            if chain_v2.rag_chain is None:
                logger.error("❌ [Stream] RAG chain is None!")
                yield f"data: {json.dumps({'type': 'error', 'message': 'RAG system not initialized'})}\n\n"
                return
            
            logger.info("🤖 [Stream] Generating response via BitNet...")
            # LangChain .invoke() call
            answer = chain_v2.rag_chain.invoke(question)
            
            yield f"data: {json.dumps({'type': 'token', 'text': str(answer)})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            
        except Exception as e:
            logger.error(f"💥 [Stream] Error: {str(e)}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")

# --- AUTH ENDPOINTS (Kept as is) ---
@app.post('/api/send-verification-code')
async def send_code(req: SendCodeRequest):
    users = load_users()
    if req.email in users: raise HTTPException(status_code=400, detail='Email registered')
    code = generate_verification_code(req.email)
    send_verification_email(req.email, code)
    return {'message': 'Sent'}

@app.post('/api/verify-code')
async def verify_v_code(req: VerifyCodeRequest):
    if not verify_code(req.email, req.code): raise HTTPException(status_code=400, detail='Invalid')
    return {'message': 'Verified'}

@app.post('/api/register')
async def register(user: UserRegister):
    if not create_user(user.email, user.password, user.role): raise HTTPException(status_code=400)
    access_token = create_access_token(data={'sub': user.email, 'role': user.role})
    return {'access_token': access_token, 'token_type': 'bearer', 'email': user.email, 'role': user.role}

@app.post('/api/login', response_model=Token)
async def login(user: UserLogin):
    auth_user = authenticate_user(user.email, user.password)
    if not auth_user: raise HTTPException(status_code=401)
    access_token = create_access_token(data={'sub': user.email, 'role': auth_user['role']})
    return {'access_token': access_token, 'token_type': 'bearer', 'email': user.email, 'role': auth_user['role']}