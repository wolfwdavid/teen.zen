import os
import logging
import json
import chain_v2
from typing import Optional
from datetime import timedelta
from fastapi import FastAPI, HTTPException, Query, Header
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
    decode_access_token,
    verify_google_token,
    get_or_create_google_user,
    get_user_by_id,
    save_chat_message,
    get_chat_history,
    clear_chat_history,
    create_task,
    get_tasks_for_user,
    get_tasks_assigned_by,
    update_task_status,
    get_all_users_for_provider,
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
    migrate_db()
    chain_v2.initialize_global_vars()
    logger.info("✅ RAG chain initialized and ready for requests.")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- HELPERS ---
def get_current_user(authorization: str = Header(None)):
    """Extract user from JWT token in Authorization header"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.replace("Bearer ", "")
    payload = decode_access_token(token)
    
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    user = get_user_by_id(payload.get("user_id"))
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    return user


# --- MODELS ---
class ChatRequest(BaseModel):
    question: str


class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    confirm_password: str
    age: int
    role: str = "user"
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

    @validator('role')
    def role_valid(cls, v):
        if v not in ('user', 'provider'):
            raise ValueError('Role must be user or provider')
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


class CreateTaskRequest(BaseModel):
    title: str
    description: str = ""
    assigned_to: int
    due_date: Optional[str] = None

    @validator('title')
    def title_valid(cls, v):
        if len(v) < 1:
            raise ValueError('Title is required')
        return v


class UpdateTaskRequest(BaseModel):
    status: str

    @validator('status')
    def status_valid(cls, v):
        if v not in ('pending', 'completed'):
            raise ValueError('Status must be pending or completed')
        return v


class SaveChatRequest(BaseModel):
    role: str
    text: str
    sources: Optional[str] = None
    timing: Optional[float] = None


# --- AUTH ENDPOINTS ---
@app.post("/api/auth/google")
async def google_auth(request: GoogleAuthRequest):
    try:
        google_info = verify_google_token(request.token)
        user = get_or_create_google_user(google_info)

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
                "email": user['email'],
                "role": user.get('role', 'user')
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        logger.error(f"Google auth error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Google sign-in failed: {str(e)}")


@app.post("/api/auth/register")
async def register(request: RegisterRequest):
    try:
        user = create_user(
            username=request.username,
            email=request.email,
            password=request.password,
            role=request.role,
            age=request.age,
            phone=request.phone
        )

        return {
            "success": True,
            "message": "Registration successful! Please check your email for a verification code.",
            "user": {
                "id": user['id'],
                "username": user['username'],
                "email": user['email'],
                "role": user.get('role', 'user')
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
            "email": user['email'],
            "role": user.get('role', 'user')
        }
    }


@app.get("/api/auth/verify-email/{token}")
async def verify_email(token: str):
    success = verify_email_token(token)
    if not success:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    return {"success": True, "message": "Email verified successfully!"}


# --- PROFILE ENDPOINT ---
@app.get("/api/profile")
async def get_profile(authorization: str = Header(None)):
    user = get_current_user(authorization)
    return {
        "id": user['id'],
        "username": user['username'],
        "email": user['email'],
        "role": user.get('role', 'user'),
        "age": user.get('age'),
        "phone": user.get('phone'),
        "created_at": user.get('created_at'),
        "last_login": user.get('last_login')
    }


# --- CHAT HISTORY ENDPOINTS ---
@app.get("/api/chat/history")
async def get_history(authorization: str = Header(None)):
    user = get_current_user(authorization)
    messages = get_chat_history(user['id'])
    return {"messages": messages}


@app.post("/api/chat/history")
async def save_message(request: SaveChatRequest, authorization: str = Header(None)):
    user = get_current_user(authorization)
    save_chat_message(user['id'], request.role, request.text, request.sources, request.timing)
    return {"success": True}


@app.delete("/api/chat/history")
async def delete_history(authorization: str = Header(None)):
    user = get_current_user(authorization)
    clear_chat_history(user['id'])
    return {"success": True, "message": "Chat history cleared"}


# --- TASK ENDPOINTS ---
@app.get("/api/tasks")
async def get_tasks(authorization: str = Header(None)):
    user = get_current_user(authorization)
    role = user.get('role', 'user')

    if role == 'provider':
        tasks = get_tasks_assigned_by(user['id'])
    else:
        tasks = get_tasks_for_user(user['id'])

    return {"tasks": tasks, "role": role}


@app.post("/api/tasks")
async def create_new_task(request: CreateTaskRequest, authorization: str = Header(None)):
    user = get_current_user(authorization)

    if user.get('role') != 'provider':
        raise HTTPException(status_code=403, detail="Only providers can create tasks")

    task_id = create_task(
        title=request.title,
        description=request.description,
        assigned_by=user['id'],
        assigned_to=request.assigned_to,
        due_date=request.due_date
    )

    return {"success": True, "task_id": task_id, "message": "Task created successfully"}


@app.put("/api/tasks/{task_id}")
async def update_task(task_id: int, request: UpdateTaskRequest, authorization: str = Header(None)):
    user = get_current_user(authorization)

    success = update_task_status(task_id, user['id'], request.status)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found or not assigned to you")

    return {"success": True, "message": f"Task marked as {request.status}"}


@app.get("/api/users")
async def get_users_list(authorization: str = Header(None)):
    """Get list of users (for providers to assign tasks)"""
    user = get_current_user(authorization)

    if user.get('role') != 'provider':
        raise HTTPException(status_code=403, detail="Only providers can view user list")

    users = get_all_users_for_provider()
    return {"users": users}


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
                yield f"data: {json.dumps({'type': 'error', 'message': 'RAG system not initialized'})}\n\n"
                return

            answer = chain_v2.rag_chain.invoke(question)
            yield f"data: {json.dumps({'type': 'token', 'text': str(answer)})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        except Exception as e:
            logger.error(f"💥 [Stream] Error: {str(e)}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")