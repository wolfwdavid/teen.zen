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

# Import authentication functions from our fixed auth.py
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

import chain_v2  # import the module

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('api_v2')

app = FastAPI(title='RAG Chatbot – V2')

# ------------------------------------------------------------------------------
# CORS (Updated to specifically allow your Svelte port 5174)
# ------------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------------------
# Models
# ------------------------------------------------------------------------------
class ChatRequest(BaseModel):
    question: str
    k: Optional[int] = None

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
    role: str = 'user'

class Token(BaseModel):
    access_token: str
    token_type: str
    email: str
    role: str

# ------------------------------------------------------------------------------
# Health Check (Crucial for turning the red dot GREEN)
# ------------------------------------------------------------------------------
@app.get('/health')
def health():
    # We return "status": "online" because your frontend checks for this specific key
    return {
        'status': 'online',
        'initialized': getattr(chain_v2.state, 'initialized', False),
        'model_loaded': getattr(chain_v2.state, 'model_loaded', False),
        'rag_ready': chain_v2.rag_chain is not None
    }

# ------------------------------------------------------------------------------
# Verification Code Endpoints
# ------------------------------------------------------------------------------
@app.post('/api/send-verification-code')
async def send_code(req: SendCodeRequest):
    users = load_users()
    if req.email in users:
        raise HTTPException(status_code=400, detail='Email already registered')
    
    code = generate_verification_code(req.email)
    success = send_verification_email(req.email, code)
    
    # Check your Python terminal for this code!
    logger.info('--- VERIFICATION CODE FOR %s: %s ---', req.email, code)
    
    return {
        'message': 'Verification code sent', 
        'expires_in': 300,
        'dev_mode': True 
    }

@app.post('/api/verify-code')
async def verify_verification_code(req: VerifyCodeRequest):
    is_valid = verify_code(req.email, req.code)
    if not is_valid:
        raise HTTPException(status_code=400, detail='Invalid or expired code')
    
    return {'message': 'Code verified successfully', 'email': req.email}

# ------------------------------------------------------------------------------
# Authentication Endpoints
# ------------------------------------------------------------------------------
@app.post('/api/register')
async def register(user: UserRegister):
    if len(user.password) < 8:
        raise HTTPException(status_code=400, detail='Password must be at least 8 characters')
    
    result = create_user(user.email, user.password, user.role)
    if not result:
        raise HTTPException(status_code=400, detail='User already exists')
    
    # Create token so the user is logged in immediately after signing up
    access_token = create_access_token(data={'sub': user.email, 'role': user.role})
    
    return {
        'message': 'User created', 
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

# ... [The /chat and /chat/stream logic remains the same below] ...