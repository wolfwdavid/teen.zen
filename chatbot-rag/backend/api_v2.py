import os
import logging
import time
import json
import asyncio
import threading
from urllib.parse import unquote
from typing import Optional, Any, Dict, List, Union
from datetime import timedelta

from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr
from dotenv import load_dotenv

# Import authentication functions
from auth import (
    create_user, 
    authenticate_user, 
    create_access_token, 
    ACCESS_TOKEN_EXPIRE_MINUTES,
    generate_verification_code,
    send_verification_email,
    verify_code,
    load_users
)

load_dotenv()

# Ensure chain_v2 has an 'ask' or 'get_response' function
import chain_v2  

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('api_v2')

app = FastAPI(title='RAG Chatbot – V2')

# Initialize RAG chain on module load
print('🚀 Initializing RAG chain...')
chain_v2.initialize_global_vars()
print('✅ RAG chain ready')

# --- CORS Setup ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For development; narrow this down for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Models ---
class ChatRequest(BaseModel):
    question: str
    k: Optional[int] = 3

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

# --- Initialize RAG on startup ---
@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Starting up API server...")
    chain_v2.initialize_global_vars()
    logger.info("✅ RAG chain initialized")

# --- Endpoints ---

@app.get('/health')
def health():
    state = chain_v2.state
    return {
        "ok": True,
        "initialized": state.initialized,
        "model_loaded": state.model_loaded,
        "init_error": state.init_error,
        "rag_chain_is_none": chain_v2.rag_chain is None,
        "retriever_is_none": chain_v2.retriever is None,
        "vectorstore_is_none": chain_v2.vectorstore is None
    }

@app.post('/api/send-verification-code')
async def send_code(req: SendCodeRequest):
    users = load_users()
    if req.email in users:
        raise HTTPException(status_code=400, detail='Email already registered')
    code = generate_verification_code(req.email)
    send_verification_email(req.email, code)
    logger.info('[DEV MODE] Verification code for %s: %s', req.email, code)
    return {'message': 'Verification code sent', 'expires_in': 300, 'dev_mode': True}

@app.post('/api/verify-code')
async def verify_verification_code(req: VerifyCodeRequest):
    if not verify_code(req.email, req.code):
        raise HTTPException(status_code=400, detail='Invalid or expired code')
    return {'message': 'Code verified successfully'}

@app.post('/api/register')
async def register(user: UserRegister):
    if len(user.password) < 8:
        raise HTTPException(status_code=400, detail='Password too short')
    if not create_user(user.email, user.password, user.role):
        raise HTTPException(status_code=400, detail='User already exists')
    
    access_token = create_access_token(data={'sub': user.email, 'role': user.role})
    return {
        'access_token': access_token, 
        'token_type': 'bearer',
        'email': user.email,
        'role': user.role
    }

@app.post('/api/login', response_model=Token)
async def login(user: UserLogin):
    auth_user = authenticate_user(user.email, user.password)
    if not auth_user:
        raise HTTPException(status_code=401, detail='Invalid credentials')
    
    access_token = create_access_token(data={'sub': user.email, 'role': auth_user['role']})
    return {
        'access_token': access_token,
        'token_type': 'bearer',
        'email': user.email,
        'role': auth_user['role']
    }

# --- Chat Interaction Endpoint ---
@app.post('/api/chat')
async def chat(req: ChatRequest):
    try:
        if chain_v2.rag_chain is None:
            raise HTTPException(status_code=503, detail="RAG system not initialized")
        
        answer = chain_v2.rag_chain.invoke(req.question)
        return {"answer": answer}
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal chatbot error")

@app.get('/api/chat/stream')
async def chat_stream(question: str = Query(...)):
    async def event_generator():
        try:
            print(f"🔍 [Stream] Question received: {question}")
            
            if chain_v2.rag_chain is None:
                print("❌ [Stream] RAG chain is None!")
                yield f"data: {json.dumps({'error': 'RAG system not initialized'})}\n\n"
                return
            
            print("🤖 [Stream] Calling invoke...")
            answer = chain_v2.rag_chain.invoke(question)
            print(f"✅ [Stream] Got answer: {answer[:100]}...")
            
            yield f"data: {json.dumps({'type': 'token', 'text': answer})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            print("📤 [Stream] Sent response")
        except Exception as e:
            print(f"💥 [Stream] Error: {str(e)}")
            logger.error(f"Stream error: {str(e)}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")