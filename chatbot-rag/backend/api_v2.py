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

import chain_v2  # import the module, not variables

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('api_v2')

app = FastAPI(title='RAG Chatbot – V2')

# ------------------------------------------------------------------------------
# CORS (✅ Android/Capacitor safe)
# ------------------------------------------------------------------------------
cors_env = (os.getenv('CORS_ORIGINS') or '').strip()
if cors_env:
    ALLOW_ORIGINS = [o.strip() for o in cors_env.split(',') if o.strip()]
else:
    # Safe defaults for local dev + Capacitor
    ALLOW_ORIGINS = [
        'http://localhost:5173',
        'http://127.0.0.1:5173',
        'http://localhost',
        'http://127.0.0.1',
        'capacitor://localhost',
        'ionic://localhost',
    ]

ALLOW_CREDENTIALS = os.getenv('CORS_ALLOW_CREDENTIALS', '1') == '1'

if '*' in ALLOW_ORIGINS and ALLOW_CREDENTIALS:
    logger.warning('CORS: * cannot be used with allow_credentials=True. Disabling credentials.')
    ALLOW_CREDENTIALS = False

app.add_middleware(
   CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=False,
    allow_methods=['*'],
    allow_headers=['*'],
    expose_headers=['*'],
)

logger.info('CORS allow_origins=%s allow_credentials=%s', ALLOW_ORIGINS, ALLOW_CREDENTIALS)


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
# Verification Code Endpoints
# ------------------------------------------------------------------------------
@app.post('/api/send-verification-code')
async def send_code(req: SendCodeRequest):
    '''Send 6-digit verification code to email'''
    # Check if user already exists
    users = load_users()
    if req.email in users:
        raise HTTPException(
            status_code=400,
            detail='Email already registered'
        )
    
    # Generate and send code
    code = generate_verification_code(req.email)
    success = send_verification_email(req.email, code)
    
    if not success:
        # In dev mode without email config, still return success
        logger.info('DEV MODE: Verification code for %s: %s', req.email, code)
    
    logger.info('Verification code sent to: %s', req.email)
    return {
        'message': 'Verification code sent', 
        'expires_in': 300,  # 5 minutes in seconds
        'dev_mode': not success  # Let frontend know if in dev mode
    }

@app.post('/api/verify-code')
async def verify_verification_code(req: VerifyCodeRequest):
    '''Verify the 6-digit code'''
    is_valid = verify_code(req.email, req.code)
    
    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail='Invalid or expired verification code'
        )
    
    logger.info('Code verified for: %s', req.email)
    return {'message': 'Code verified successfully', 'email': req.email}


# ------------------------------------------------------------------------------
# Authentication Endpoints
# ------------------------------------------------------------------------------
@app.post('/api/register', response_model=dict)
async def register(user: UserRegister):
    '''Register a new user (requires prior code verification)'''
    if len(user.password) < 8:
        raise HTTPException(
            status_code=400,
            detail='Password must be at least 8 characters'
        )
    
    result = create_user(user.email, user.password, user.role)
    if not result:
        raise HTTPException(
            status_code=400,
            detail='User already exists'
        )
    
    logger.info('New user registered: %s (role: %s)', user.email, user.role)
    return {'message': 'User created successfully', 'email': user.email, 'role': user.role}

@app.post('/api/login', response_model=Token)
async def login(user: UserLogin):
    '''Login user and return JWT token'''
    authenticated_user = authenticate_user(user.email, user.password)
    
    if not authenticated_user:
        raise HTTPException(
            status_code=401,
            detail='Incorrect email or password'
        )
    
    # Check if role matches
    if authenticated_user['role'] != user.role:
        raise HTTPException(
            status_code=403,
            detail='Invalid role for this account'
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={'sub': user.email, 'role': user.role},
        expires_delta=access_token_expires
    )
    
    logger.info('User logged in: %s (role: %s)', user.email, user.role)
    
    return {
        'access_token': access_token,
        'token_type': 'bearer',
        'email': user.email,
        'role': user.role
    }


# ------------------------------------------------------------------------------
# Startup
# ------------------------------------------------------------------------------
@app.on_event('startup')
def on_startup():
    logger.info('🔧 Startup (V2): initializing RAG + model...')
    st = chain_v2.initialize_global_vars(force=False)
    logger.info('Startup state: %s', st)


# ------------------------------------------------------------------------------
# Health
# ------------------------------------------------------------------------------
@app.get('/health')
def health():
    vectorstore_is_none = getattr(chain_v2, 'vectorstore', None) is None

    return {
        'ok': True,
        'initialized': chain_v2.state.initialized,
        'model_loaded': chain_v2.state.model_loaded,
        'init_error': chain_v2.state.init_error,
        'rag_chain_is_none': chain_v2.rag_chain is None,
        'retriever_is_none': chain_v2.retriever is None,
        'vectorstore_is_none': vectorstore_is_none,
        
    }


def _require_ready():
    if (not chain_v2.state.model_loaded) or (chain_v2.rag_chain is None) or (chain_v2.retriever is None):
        raise HTTPException(
            status_code=503,
            detail={
                'error': 'Model not loaded',
                'initialized': chain_v2.state.initialized,
                'model_loaded': chain_v2.state.model_loaded,
                'init_error': chain_v2.state.init_error,
                'rag_chain_is_none': chain_v2.rag_chain is None,
                'retriever_is_none': chain_v2.retriever is None,
            },
        )


def _sse(obj: Dict[str, Any]) -> str:
    return f'data: {json.dumps(obj, ensure_ascii=False)}\n\n'


def _get_sources_safe(question: str, k: int) -> List[Dict[str, Any]]:
    try:
        return chain_v2.get_sources(question, k=k)
    except TypeError:
        return chain_v2.get_sources(question, chain_v2.retriever, k=k)


# ------------------------------------------------------------------------------
# POST /chat
# ------------------------------------------------------------------------------
@app.post('/chat')
async def chat(req: ChatRequest):
    _require_ready()

    question = (req.question or '').strip()
    if not question:
        raise HTTPException(status_code=400, detail='Missing question')

    k = int(req.k) if req.k is not None else 3

    answer = chain_v2.rag_chain.invoke(question)

    if answer.strip() == 'I dont know.':
        return {'answer': answer, 'sources': []}

    srcs = _get_sources_safe(question, k=k)
    return {'answer': answer, 'sources': srcs}


# ------------------------------------------------------------------------------
# GET /chat/stream (SSE)
# ------------------------------------------------------------------------------
@app.get('/chat/stream')
async def chat_stream(
    request: Request,
    q: str = Query(..., description='User question'),
    k: int = Query(3, ge=1, le=20, description='Top-K sources to retrieve'),
    debug: int = Query(0, ge=0, le=1, description='Include extra debug fields in SSE payloads'),
    heartbeat: float = Query(2.0, ge=0.0, le=10.0, description='Heartbeat seconds (0 disables)'),
):
    _require_ready()

    question = unquote(q or '').strip()
    if not question:
        raise HTTPException(status_code=400, detail='Missing query parameter q')

    async def event_gen():
        start_time = time.time()

        gated_answer = chain_v2.rag_chain.invoke(question)

        if gated_answer.strip() == 'I dont know.':
            yield _sse({'type': 'sources', 'items': []})
            yield _sse({'type': 'token', 'text': 'I dont know.'})
            elapsed = time.time() - start_time
            yield _sse({'type': 'perf_time', 'data': f'{elapsed:.2f}'})
            yield _sse({'type': 'done'})
            return

        try:
            srcs = _get_sources_safe(question, k=k)
        except Exception as e:
            srcs = []
            logger.exception('get_sources failed: %s', e)

        payload: Dict[str, Any] = {'type': 'sources', 'items': srcs}
        if debug:
            payload['debug'] = {
                'k': k,
                'initialized': chain_v2.state.initialized,
                'model_loaded': chain_v2.state.model_loaded,
                'init_error': chain_v2.state.init_error,
            }
        yield _sse(payload)

        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[Optional[Union[str, Dict[str, Any]]]] = asyncio.Queue()
        stop_flag = threading.Event()

        def producer():
            try:
                for chunk in chain_v2.rag_chain.stream(question):
                    if stop_flag.is_set():
                        break
                    asyncio.run_coroutine_threadsafe(queue.put(str(chunk)), loop)
            except Exception as e:
                logger.exception('Stream producer error: %s', e)
                asyncio.run_coroutine_threadsafe(queue.put({'type': 'error', 'error': str(e)}), loop)
            finally:
                asyncio.run_coroutine_threadsafe(queue.put(None), loop)

        threading.Thread(target=producer, daemon=True).start()

        last_heartbeat = time.time()

        while True:
            if await request.is_disconnected():
                stop_flag.set()
                break

            if heartbeat and (time.time() - last_heartbeat) >= heartbeat:
                last_heartbeat = time.time()
                yield ':\n\n'

            try:
                item = await asyncio.wait_for(queue.get(), timeout=0.25)
            except asyncio.TimeoutError:
                continue

            if item is None:
                break

            if isinstance(item, dict):
                yield _sse(item)
                continue

            yield _sse({'type': 'token', 'text': item})

        elapsed = time.time() - start_time
        yield _sse({'type': 'perf_time', 'data': f'{elapsed:.2f}'})
        yield _sse({'type': 'done'})

    return StreamingResponse(
        event_gen(),
        media_type='text/event-stream; charset=utf-8',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no',
        },
    )