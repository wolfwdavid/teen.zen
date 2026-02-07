import os
import logging
import json
import chain_v2
from typing import Optional
from datetime import timedelta
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr, validator
from auth import (
    create_user,
    authenticate_user,
    verify_email_token,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    get_user_by_email
)
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('api_v2')

app = FastAPI(title='RAG Chatbot – V2')

@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Starting up API server...")
    chain_v2.initialize_global_vars()
    logger.info("✅ RAG chain initialized and ready for requests.")

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

class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    confirm_password: str
    age: int
    phone: Optional[str] = None
    
    @validator('username')
    def username_valid(cls, v):
        if len(v) < 3:
            raise ValueError('Username must be at least 3 characters')
        if not v.isalnum():
            raise ValueError('Username must be alphanumeric')
        return v
    
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v
    
    @validator('age')
    def age_valid(cls, v):
        if v < 13:
            raise ValueError('Must be at least 13 years old')
        if v > 120:
            raise ValueError('Invalid age')
        return v

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

# --- AUTH ENDPOINTS ---
@app.post("/api/auth/register")
async def register(request: RegisterRequest):
    """Register a new user"""
    try:
        user = create_user(
            username=request.username,
            email=request.email,
            password=request.password,
            age=request.age,
            phone=request.phone
        )
        
        return {
            "success": True,
            "message": "Registration successful! Please check your email to verify your account.",
            "user": {
                "id": user['id'],
                "username": user['username'],
                "email": user['email']
            },
            "verification_token": user['verification_token']
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@app.post("/api/auth/login")
async def login(request: LoginRequest):
    """Login user and return JWT token"""
    user = authenticate_user(request.email, request.password)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if not user['email_verified']:
        raise HTTPException(status_code=403, detail="Please verify your email first")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user['email'], "user_id": user['id']},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user['id'],
            "username": user['username'],
            "email": user['email']
        }
    }

@app.get("/api/auth/verify-email/{token}")
async def verify_email(token: str):
    """Verify user email with token"""
    success = verify_email_token(token)
    
    if not success:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    
    return {"success": True, "message": "Email verified successfully!"}

# --- HEALTH & CHAT ENDPOINTS ---
@app.get('/health')
def health():
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
        if chain_v2.rag_chain is None:
            raise HTTPException(status_code=503, detail="RAG system not initialized")
        
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
            
            if chain_v2.rag_chain is None:
                logger.error("❌ [Stream] RAG chain is None!")
                yield f"data: {json.dumps({'type': 'error', 'message': 'RAG system not initialized'})}\n\n"
                return
            
            logger.info("🤖 [Stream] Generating response...")
            answer = chain_v2.rag_chain.invoke(question)
            
            yield f"data: {json.dumps({'type': 'token', 'text': str(answer)})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            
        except Exception as e:
            logger.error(f"💥 [Stream] Error: {str(e)}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")