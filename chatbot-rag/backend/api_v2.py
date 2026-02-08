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
    verify_email_pin,
    resend_verification_pin,
    create_access_token,
    verify_google_token,
    get_or_create_google_user,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    get_user_by_email
)
from database import migrate_db
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('api_v2')

app = FastAPI(title='RAG Chatbot – V2')


@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Starting up API server...")
    migrate_db()  # Ensure database has latest schema
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

    @validator('password')
    def password_strong(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if len(v) > 72:
            raise ValueError('Password cannot be longer than 72 characters')
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


class VerifyPinRequest(BaseModel):
    email: EmailStr
    pin: str

    @validator('pin')
    def pin_valid(cls, v):
        if len(v) != 6 or not v.isdigit():
            raise ValueError('PIN must be exactly 6 digits')
        return v


class ResendPinRequest(BaseModel):
    email: EmailStr


class GoogleAuthRequest(BaseModel):
    token: str


# --- AUTH ENDPOINTS ---
@app.post("/api/auth/google")
async def google_auth(request: GoogleAuthRequest):
    """Authenticate with Google OAuth token"""
    try:
        # Verify the Google token
        google_info = verify_google_token(request.token)
        
        # Get or create user
        user = get_or_create_google_user(google_info)
        
        # Create JWT token
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
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        logger.error(f"Google auth error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Google sign-in failed: {str(e)}")


@app.post("/api/auth/register")
async def register(request: RegisterRequest):
    """Register a new user and send verification PIN via email"""
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
            "message": "Registration successful! Please check your email for a verification code.",
            "user": {
                "id": user['id'],
                "username": user['username'],
                "email": user['email']
            },
            "email_sent": user.get('email_sent', False)
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")


@app.post("/api/auth/verify-pin")
async def verify_pin(request: VerifyPinRequest):
    """Verify email with 6-digit PIN"""
    try:
        success = verify_email_pin(request.email, request.pin)

        if not success:
            raise HTTPException(status_code=400, detail="Invalid verification code")

        return {"success": True, "message": "Email verified successfully! You can now sign in."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Verification error: {str(e)}")
        raise HTTPException(status_code=500, detail="Verification failed")


@app.post("/api/auth/resend-pin")
async def resend_pin(request: ResendPinRequest):
    """Resend verification PIN to email"""
    try:
        success = resend_verification_pin(request.email)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to send verification email")

        return {"success": True, "message": "A new verification code has been sent to your email."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Resend error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to resend verification code")


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
    """Verify user email with token (legacy)"""
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