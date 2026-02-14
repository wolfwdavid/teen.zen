import os
import logging
import json
import chain_v2
from typing import Optional
from datetime import timedelta, datetime, timezone
from fastapi import FastAPI, HTTPException, Query, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import urllib.request
from pydantic import BaseModel, EmailStr, validator
from auth import (
    create_user, authenticate_user, verify_email_token, verify_email_pin,
    resend_verification_pin, create_access_token, decode_access_token,
    verify_google_token, get_or_create_google_user, get_user_by_id,
    save_chat_message, get_chat_history, clear_chat_history,
    get_available_quarters, get_current_quarter,
    get_chat_history_for_archive, create_archive_record,
    get_archives_for_provider, get_provider_for_user,
    create_task, get_tasks_for_user, get_tasks_assigned_by,
    update_task_status, get_all_users_for_provider,
    # Provider-patient management
    get_provider_patients, get_patient_count, assign_patient_to_provider,
    remove_patient_from_provider, auto_assign_patient,
    # Clinical data
    save_clinical_intake, get_clinical_intake,
    save_therapist_observations, get_therapist_observations,
    # Forgot password
    send_reset_pin, verify_reset_and_change_password,
    # Knowledge graph
    extract_knowledge_graph,
    # Profile picture
    save_profile_pic, get_profile_pic,
    # Provider info for users
    get_provider_info_for_user,
    ACCESS_TOKEN_EXPIRE_MINUTES, get_user_by_email,
    MAX_PATIENTS_PER_PROVIDER
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
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)


# --- HELPERS ---
def get_current_user(authorization: str = Header(None)):
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


def require_provider(user):
    if user.get('role') != 'provider':
        raise HTTPException(status_code=403, detail="Only providers can access this")
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
        if len(v) < 3: raise ValueError('Username must be at least 3 characters')
        if not v.isalnum(): raise ValueError('Username must be alphanumeric')
        return v
    @validator('password')
    def password_strong(cls, v):
        if len(v) < 8: raise ValueError('Password must be at least 8 characters')
        if len(v) > 72: raise ValueError('Password cannot be longer than 72 characters')
        return v
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'password' in values and v != values['password']: raise ValueError('Passwords do not match')
        return v
    @validator('age')
    def age_valid(cls, v):
        if v < 13: raise ValueError('Must be at least 13 years old')
        if v > 120: raise ValueError('Invalid age')
        return v
    @validator('role')
    def role_valid(cls, v):
        if v not in ('user', 'provider'): raise ValueError('Role must be user or provider')
        return v

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class VerifyPinRequest(BaseModel):
    email: EmailStr
    pin: str
    @validator('pin')
    def pin_valid(cls, v):
        if len(v) != 6 or not v.isdigit(): raise ValueError('PIN must be exactly 6 digits')
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

class UpdateTaskRequest(BaseModel):
    status: str
    @validator('status')
    def status_valid(cls, v):
        if v not in ('pending', 'completed'): raise ValueError('Status must be pending or completed')
        return v

class SaveChatRequest(BaseModel):
    role: str
    text: str
    sources: Optional[str] = None
    timing: Optional[float] = None

class ClinicalDataRequest(BaseModel):
    intake_data: dict

class ObservationsRequest(BaseModel):
    observations: dict

class AssignPatientRequest(BaseModel):
    user_id: int

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    pin: str
    new_password: str
    @validator('pin')
    def pin_valid(cls, v):
        if len(v) != 6 or not v.isdigit(): raise ValueError('PIN must be exactly 6 digits')
        return v
    @validator('new_password')
    def password_strong(cls, v):
        if len(v) < 8: raise ValueError('Password must be at least 8 characters')
        return v


# --- AUTH ENDPOINTS ---
@app.post("/api/auth/google")
async def google_auth(request: GoogleAuthRequest):
    try:
        google_info = verify_google_token(request.token)
        user = get_or_create_google_user(google_info)
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(data={"sub": user['email'], "user_id": user['id']}, expires_delta=access_token_expires)
        return {"access_token": access_token, "token_type": "bearer",
                "user": {"id": user['id'], "username": user['username'], "email": user['email'], "role": user.get('role', 'user')}}
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        logger.error(f"Google auth error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Google sign-in failed: {str(e)}")


@app.post("/api/auth/register")
async def register(request: RegisterRequest):
    try:
        user = create_user(username=request.username, email=request.email, password=request.password,
                           role=request.role, age=request.age, phone=request.phone)
        return {"success": True, "message": "Registration successful! Please check your email for a verification code.",
                "user": {"id": user['id'], "username": user['username'], "email": user['email'], "role": user.get('role', 'user')},
                "email_sent": user.get('email_sent', False)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")


@app.post("/api/auth/verify-pin")
async def verify_pin(request: VerifyPinRequest):
    try:
        success = verify_email_pin(request.email, request.pin)
        if not success: raise HTTPException(status_code=400, detail="Invalid verification code")
        return {"success": True, "message": "Email verified successfully! You can now sign in."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException: raise
    except Exception as e:
        logger.error(f"Verification error: {str(e)}")
        raise HTTPException(status_code=500, detail="Verification failed")


@app.post("/api/auth/resend-pin")
async def resend_pin(request: ResendPinRequest):
    try:
        success = resend_verification_pin(request.email)
        if not success: raise HTTPException(status_code=500, detail="Failed to send verification email")
        return {"success": True, "message": "A new verification code has been sent to your email."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException: raise
    except Exception as e:
        logger.error(f"Resend error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to resend verification code")


@app.post("/api/auth/login")
async def login(request: LoginRequest):
    user = authenticate_user(request.email, request.password)
    if not user: raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user['email_verified']: raise HTTPException(status_code=403, detail="Please verify your email first")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user['email'], "user_id": user['id']}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer",
            "user": {"id": user['id'], "username": user['username'], "email": user['email'], "role": user.get('role', 'user')}}


@app.get("/api/auth/verify-email/{token}")
async def verify_email(token: str):
    success = verify_email_token(token)
    if not success: raise HTTPException(status_code=400, detail="Invalid or expired token")
    return {"success": True, "message": "Email verified successfully!"}


# --- FORGOT PASSWORD ---
@app.post("/api/auth/forgot-password")
async def forgot_password(request: ForgotPasswordRequest):
    try:
        success = send_reset_pin(request.email)
        if not success: raise HTTPException(status_code=500, detail="Failed to send reset email")
        return {"success": True, "message": "A password reset code has been sent to your email."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException: raise
    except Exception as e:
        logger.error(f"Forgot password error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to process request")

@app.post("/api/auth/reset-password")
async def reset_password(request: ResetPasswordRequest):
    try:
        success = verify_reset_and_change_password(request.email, request.pin, request.new_password)
        if not success: raise HTTPException(status_code=400, detail="Invalid reset code")
        return {"success": True, "message": "Password reset successfully! You can now sign in."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException: raise
    except Exception as e:
        logger.error(f"Reset password error: {str(e)}")
        raise HTTPException(status_code=500, detail="Password reset failed")


# --- PROFILE ---
@app.get("/api/profile")
async def get_profile(authorization: str = Header(None)):
    user = get_current_user(authorization)
    result = {"id": user['id'], "username": user['username'], "email": user['email'],
              "role": user.get('role', 'user'), "age": user.get('age'), "phone": user.get('phone'),
              "created_at": user.get('created_at'), "last_login": user.get('last_login')}
    pic = get_profile_pic(user['id'])
    if pic: result['profile_pic'] = pic
    if user.get('role') == 'provider':
        result['patient_count'] = get_patient_count(user['id'])
        result['max_patients'] = MAX_PATIENTS_PER_PROVIDER
    return result

@app.post("/api/profile/pic")
async def upload_profile_pic(request: Request, authorization: str = Header(None)):
    user = get_current_user(authorization)
    body = await request.json()
    pic_data = body.get('pic')
    if not pic_data: raise HTTPException(status_code=400, detail="No pic data")
    # Limit to ~2MB base64
    if len(pic_data) > 3_000_000: raise HTTPException(status_code=400, detail="Image too large (max 2MB)")
    save_profile_pic(user['id'], pic_data)
    return {"success": True}

@app.delete("/api/profile/pic")
async def delete_profile_pic(authorization: str = Header(None)):
    user = get_current_user(authorization)
    save_profile_pic(user['id'], None)

# --- USER PROFILE DATA (synced from client) ---
@app.post("/api/profile/data")
async def save_profile_data(request: Request, authorization: str = Header(None)):
    user = get_current_user(authorization)
    body = await request.json()
    profile_data = body.get('profile_data', {})
    from auth import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()
    data_json = json.dumps(profile_data)
    now = datetime.utcnow().isoformat()
    cursor.execute("""
        INSERT INTO user_profile_data (user_id, profile_data, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id)
        DO UPDATE SET profile_data = ?, updated_at = ?
    """, (user['id'], data_json, now, data_json, now))
    conn.commit()
    conn.close()
    return {"success": True}

@app.get("/api/profile/data")
async def get_profile_data(authorization: str = Header(None)):
    user = get_current_user(authorization)
    from auth import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT profile_data FROM user_profile_data WHERE user_id = ?', (user['id'],))
    row = cursor.fetchone()
    conn.close()
    if row:
        try:
            return {"data": json.loads(row['profile_data'])}
        except:
            return {"data": {}}
    return {"data": {}}

@app.get("/api/provider/patients/{user_id}/profile-data")
async def get_patient_profile_data(user_id: int, authorization: str = Header(None)):
    user = get_current_user(authorization)
    require_provider(user)
    from auth import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT profile_data FROM user_profile_data WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        try:
            return {"data": json.loads(row['profile_data'])}
        except:
            return {"data": {}}
    return {"data": {}}
    return {"success": True}


@app.get("/api/my-provider")
async def get_my_provider(authorization: str = Header(None)):
    user = get_current_user(authorization)
    provider = get_provider_info_for_user(user['id'])
    if provider:
        return {"provider": provider}
    return {"provider": None}


# --- CHAT HISTORY ---
@app.get("/api/chat/history")
async def get_history(authorization: str = Header(None), year: Optional[int] = None, quarter: Optional[int] = None, user_id: Optional[int] = None):
    user = get_current_user(authorization)
    target_id = user['id']
    all_messages = False
    # Providers can view patient chat history (all quarters)
    if user_id and user.get('role') == 'provider':
        target_id = user_id
        all_messages = True
    if all_messages:
        from auth import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''SELECT role, text, sources, timing, created_at FROM chat_messages
            WHERE user_id = ? ORDER BY created_at ASC''', (target_id,))
        rows = cursor.fetchall()
        conn.close()
        import json as jlib
        msgs = []
        for row in rows:
            msg = {"type": row['role'], "text": row['text'], "timing": row['timing'], "created_at": row['created_at']}
            if row['sources']:
                try: msg['sources'] = jlib.loads(row['sources'])
                except: msg['sources'] = []
            else: msg['sources'] = []
            msgs.append(msg)
        return {"messages": msgs}
    messages = get_chat_history(target_id, year, quarter)
    cy, cq = get_current_quarter()
    return {"messages": messages, "current_quarter": {"year": cy, "quarter": cq},
            "viewing": {"year": year or cy, "quarter": quarter or cq}}

@app.get("/api/chat/quarters")
async def get_quarters(authorization: str = Header(None)):
    user = get_current_user(authorization)
    quarters = get_available_quarters(user['id'])
    cy, cq = get_current_quarter()
    return {"quarters": quarters, "current": {"year": cy, "quarter": cq}}

@app.post("/api/chat/history")
async def save_message(request: SaveChatRequest, authorization: str = Header(None)):
    user = get_current_user(authorization)
    save_chat_message(user['id'], request.role, request.text, request.sources, request.timing)
    return {"success": True}

@app.delete("/api/chat/history")
async def delete_history(authorization: str = Header(None)):
    user = get_current_user(authorization)
    clear_chat_history(user['id'])
    return {"success": True, "message": "Chat view cleared (history preserved in archives)"}


# --- ARCHIVES ---
@app.post("/api/chat/archive")
async def archive_quarter(authorization: str = Header(None), year: Optional[int] = None, quarter: Optional[int] = None):
    user = get_current_user(authorization)
    if year is None or quarter is None:
        cy, cq = get_current_quarter()
        if cq == 1: year, quarter = cy - 1, 4
        else: year, quarter = cy, cq - 1
    messages = get_chat_history_for_archive(user['id'], year, quarter)
    if not messages: return {"success": False, "message": "No messages to archive"}
    provider_id = get_provider_for_user(user['id'])
    archive_id = create_archive_record(user['id'], provider_id, quarter, year, len(messages))
    return {"success": True, "archive_id": archive_id, "message": f"Archived Q{quarter} {year} ({len(messages)} messages)"}

@app.get("/api/archives")
async def get_archives(authorization: str = Header(None)):
    user = get_current_user(authorization)
    require_provider(user)
    archives = get_archives_for_provider(user['id'])
    return {"archives": archives}

@app.get("/api/archives/{user_id}/{year}/{quarter}/pdf")
async def get_archive_pdf(user_id: int, year: int, quarter: int, authorization: str = Header(None)):
    provider = get_current_user(authorization)
    require_provider(provider)
    target_user = get_user_by_id(user_id)
    if not target_user: raise HTTPException(status_code=404, detail="User not found")
    messages = get_chat_history_for_archive(user_id, year, quarter)
    if not messages: raise HTTPException(status_code=404, detail="No messages for this quarter")
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.colors import HexColor
        import io
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=50, bottomMargin=50)
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle('T2', parent=styles['Title'], fontSize=18, textColor=HexColor('#4F46E5'))
        meta_style = ParagraphStyle('Meta', parent=styles['Normal'], fontSize=10, textColor=HexColor('#71717A'))
        user_style = ParagraphStyle('U', parent=styles['Normal'], fontSize=11, backColor=HexColor('#EEF2FF'), leftIndent=20, rightIndent=20, spaceBefore=8, spaceAfter=4, borderPadding=8)
        bot_style = ParagraphStyle('B', parent=styles['Normal'], fontSize=11, leftIndent=20, rightIndent=20, spaceBefore=4, spaceAfter=8, borderPadding=8)
        date_style = ParagraphStyle('D', parent=styles['Normal'], fontSize=9, textColor=HexColor('#A1A1AA'), alignment=1, spaceBefore=16, spaceAfter=8)
        elements = []
        elements.append(Paragraph(f"Chat Archive — Q{quarter} {year}", title_style))
        elements.append(Spacer(1, 4))
        elements.append(Paragraph(f"User: {target_user['username']} ({target_user['email']})", meta_style))
        elements.append(Paragraph(f"Generated: {datetime.utcnow().strftime('%B %d, %Y at %H:%M UTC')}", meta_style))
        elements.append(Spacer(1, 20))
        current_date = None
        for msg in messages:
            msg_date = msg['created_at'][:10] if msg.get('created_at') else 'Unknown'
            if msg_date != current_date:
                current_date = msg_date
                try:
                    dt = datetime.strptime(msg_date, '%Y-%m-%d')
                    elements.append(Paragraph(dt.strftime('%A, %B %d, %Y'), date_style))
                except: elements.append(Paragraph(msg_date, date_style))
            role_label = "USER" if msg['role'] == 'user' else "CHATBOT"
            time_str = msg['created_at'][11:16] if msg.get('created_at') and len(msg['created_at']) > 16 else ''
            text = msg.get('text', '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            style = user_style if msg['role'] == 'user' else bot_style
            elements.append(Paragraph(f"<b>{role_label}</b> {time_str}<br/>{text}", style))
        doc.build(elements)
        buffer.seek(0)
        filename = f"chat_archive_{target_user['username']}_Q{quarter}_{year}.pdf"
        return Response(content=buffer.read(), media_type="application/pdf",
                        headers={"Content-Disposition": f"attachment; filename={filename}"})
    except ImportError:
        lines = [f"Chat Archive — Q{quarter} {year}", f"User: {target_user['username']}", "=" * 60]
        for msg in messages:
            role = "USER" if msg['role'] == 'user' else "BOT"
            lines.append(f"\n[{msg.get('created_at', '')}] {role}: {msg.get('text', '')}")
        return Response(content="\n".join(lines), media_type="text/plain",
                        headers={"Content-Disposition": f"attachment; filename=archive_{target_user['username']}_Q{quarter}_{year}.txt"})


# --- PROVIDER DASHBOARD ---
@app.get("/api/provider/patients")
async def get_patients(authorization: str = Header(None)):
    user = get_current_user(authorization)
    require_provider(user)
    patients = get_provider_patients(user['id'])
    return {"patients": patients, "count": len(patients), "max": MAX_PATIENTS_PER_PROVIDER}

@app.post("/api/provider/patients")
async def add_patient(request: AssignPatientRequest, authorization: str = Header(None)):
    user = get_current_user(authorization)
    require_provider(user)
    try:
        assign_patient_to_provider(user['id'], request.user_id)
        return {"success": True, "message": "Patient assigned successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/provider/patients/{user_id}")
async def remove_patient(user_id: int, authorization: str = Header(None)):
    user = get_current_user(authorization)
    require_provider(user)
    remove_patient_from_provider(user['id'], user_id)
    return {"success": True, "message": "Patient removed"}


# --- CLINICAL INTAKE ---
@app.get("/api/provider/patients/{user_id}/intake")
async def get_intake(user_id: int, authorization: str = Header(None)):
    user = get_current_user(authorization)
    require_provider(user)
    result = get_clinical_intake(user_id, user['id'])
    return result

@app.post("/api/provider/patients/{user_id}/intake")
async def save_intake(user_id: int, request: ClinicalDataRequest, authorization: str = Header(None)):
    user = get_current_user(authorization)
    require_provider(user)
    save_clinical_intake(user_id, user['id'], request.intake_data)
    return {"success": True, "message": "Clinical intake saved"}


# --- THERAPIST OBSERVATIONS (PRIVATE) ---
@app.get("/api/provider/patients/{user_id}/observations")
async def get_obs(user_id: int, authorization: str = Header(None)):
    user = get_current_user(authorization)
    require_provider(user)
    result = get_therapist_observations(user_id, user['id'])
    return result

@app.post("/api/provider/patients/{user_id}/observations")
async def save_obs(user_id: int, request: ObservationsRequest, authorization: str = Header(None)):
    user = get_current_user(authorization)
    require_provider(user)
    save_therapist_observations(user_id, user['id'], request.observations)
    return {"success": True, "message": "Observations saved"}


# --- KNOWLEDGE GRAPH ---
@app.get("/api/provider/patients/{user_id}/knowledge-graph")
async def get_knowledge_graph(user_id: int, authorization: str = Header(None)):
    user = get_current_user(authorization)
    require_provider(user)
    graph = extract_knowledge_graph(user_id)
    return graph


# --- TASKS ---
@app.get("/api/tasks")
async def get_tasks(authorization: str = Header(None)):
    user = get_current_user(authorization)
    role = user.get('role', 'user')
    tasks = get_tasks_assigned_by(user['id']) if role == 'provider' else get_tasks_for_user(user['id'])
    return {"tasks": tasks, "role": role}

@app.post("/api/tasks")
async def create_new_task(request: CreateTaskRequest, authorization: str = Header(None)):
    user = get_current_user(authorization)
    require_provider(user)
    task_id = create_task(title=request.title, description=request.description,
                          assigned_by=user['id'], assigned_to=request.assigned_to, due_date=request.due_date)
    return {"success": True, "task_id": task_id, "message": "Task created successfully"}

@app.put("/api/tasks/{task_id}")
async def update_task(task_id: int, request: UpdateTaskRequest, authorization: str = Header(None)):
    user = get_current_user(authorization)
    success = update_task_status(task_id, user['id'], request.status)
    if not success: raise HTTPException(status_code=404, detail="Task not found or not assigned to you")
    return {"success": True, "message": f"Task marked as {request.status}"}

@app.get("/api/users")
async def get_users_list(authorization: str = Header(None)):
    user = get_current_user(authorization)
    require_provider(user)
    users = get_all_users_for_provider()
    return {"users": users}


# --- HEALTH & CHAT ---
@app.get('/health')
def health():
    return {"ok": True, "initialized": chain_v2.state.initialized, "model_loaded": chain_v2.state.model_loaded,
            "rag_chain_is_none": chain_v2.rag_chain is None, "retriever_is_none": chain_v2.retriever is None,
            "vectorstore_is_none": chain_v2.vectorstore is None}

@app.post('/api/chat')
async def chat(req: ChatRequest):
    try:
        if chain_v2.rag_chain is None: raise HTTPException(status_code=503, detail="RAG system not initialized")
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

            # Intercept time/weather questions
            if detect_time_question(question):
                answer = get_current_time_response()
                yield f"data: {json.dumps({'type': 'token', 'text': answer})}\n\n"
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                return
            if detect_weather_question(question):
                answer = get_weather_response()
                yield f"data: {json.dumps({'type': 'token', 'text': answer})}\n\n"
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                return

            full_text = ""
            for token in chain_v2.rag_chain.stream(question):
                full_text += token
                yield f"data: {json.dumps({'type': 'token', 'text': token})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        except Exception as e:
            logger.error(f"💥 [Stream] Error: {str(e)}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get('/api/chat/provider-stream')
async def provider_chat_stream(question: str = Query(...), patient_id: Optional[int] = None, authorization: str = Header(None)):
    """Provider-aware chat that includes patient context"""
    user = get_current_user(authorization)
    require_provider(user)

    # Build context from patient data if specified
    context_parts = []
    if patient_id:
        from auth import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        # Get patient info - pull ALL available fields
        cursor.execute('SELECT username, email, age, phone, role, created_at, last_login FROM users WHERE id = ?', (patient_id,))
        patient = cursor.fetchone()
        if patient:
            profile_info = [f"Name: {patient['username']}"]
            if patient['age']:
                profile_info.append(f"Age: {patient['age']}")
            if patient['email']:
                profile_info.append(f"Email: {patient['email']}")
            if patient['phone']:
                profile_info.append(f"Phone: {patient['phone']}")
            if patient['created_at']:
                profile_info.append(f"Joined: {patient['created_at']}")
            if patient['last_login']:
                profile_info.append(f"Last active: {patient['last_login']}")
            context_parts.append("Patient Profile: " + ", ".join(profile_info))

        # Get recent chat messages
        cursor.execute('SELECT role, text, created_at FROM chat_messages WHERE user_id = ? ORDER BY created_at DESC LIMIT 10', (patient_id,))
        recent = cursor.fetchall()
        if recent:
            chat_lines = [("Patient" if r['role']=='user' else "Bot") + ": " + r['text'][:80] for r in reversed(recent)]
            context_parts.append("Chat History:\n" + "\n".join(chat_lines))

        # Get clinical intake
        try:
            cursor.execute('SELECT intake_data FROM clinical_intake WHERE user_id = ? ORDER BY updated_at DESC LIMIT 1', (patient_id,))
            intake = cursor.fetchone()
            if intake:
                try:
                    intake_data = json.loads(intake['intake_data'])
                    for key, val in intake_data.items():
                        if val:
                            context_parts.append(key.replace('_', ' ').title() + ": " + str(val))
                except: pass
        except: pass

        # Get patient clinical data
        try:
            cursor.execute('SELECT intake_data FROM patient_clinical_data WHERE user_id = ? ORDER BY updated_at DESC LIMIT 1', (patient_id,))
            clinical = cursor.fetchone()
            if clinical:
                try:
                    clinical_data = json.loads(clinical['intake_data'])
                    for key, val in clinical_data.items():
                        if val:
                            context_parts.append(key.replace('_', ' ').title() + ": " + str(val))
                except: pass
        except: pass

        # Get assigned tasks
        try:
            cursor.execute('SELECT title, description, status, due_date FROM tasks WHERE assigned_to = ? ORDER BY created_at DESC LIMIT 10', (patient_id,))
            tasks_list = cursor.fetchall()
            if tasks_list:
                task_summary = "; ".join([t['title'] + " (status: " + t['status'] + ")" for t in tasks_list])
                context_parts.append("Assigned Tasks: " + task_summary)
        except: pass

        # Get knowledge graph topics
        graph = extract_knowledge_graph(patient_id)
        if graph.get('stats', {}).get('top_topics'):
            topics = [t[0] for t in graph['stats']['top_topics'][:5]]
            context_parts.append("Key topics discussed: " + ", ".join(topics))
        # Get user profile data (name, DOB, parents, emergency contact)
        try:
            cursor.execute('SELECT profile_data FROM user_profile_data WHERE user_id = ?', (patient_id,))
            profile_row = cursor.fetchone()
            if profile_row:
                try:
                    pd = json.loads(profile_row['profile_data'])
                    profile_parts = []
                    if pd.get('fullName'): profile_parts.append('Full name: ' + pd['fullName'])
                    if pd.get('preferredName'): profile_parts.append('Goes by: ' + pd['preferredName'])
                    if pd.get('pronouns'): profile_parts.append('Pronouns: ' + pd['pronouns'])
                    if pd.get('dob'): profile_parts.append('Date of birth: ' + pd['dob'])
                    if pd.get('contactPhone'): profile_parts.append('Phone: ' + pd['contactPhone'])
                    if pd.get('parent1FullName'): profile_parts.append('Parent/Guardian 1: ' + pd['parent1FullName'] + (' (' + pd.get('parent1EmergencyRelation','') + ')' if pd.get('parent1EmergencyRelation') else ''))
                    if pd.get('parent2FullName'): profile_parts.append('Parent/Guardian 2: ' + pd['parent2FullName'] + (' (' + pd.get('parent2EmergencyRelation','') + ')' if pd.get('parent2EmergencyRelation') else ''))
                    if pd.get('emergencyName'): profile_parts.append('Emergency contact: ' + pd['emergencyName'])
                    if profile_parts:
                        context_parts.append('Profile Details: ' + ', '.join(profile_parts))
                except: pass
        except: pass
        conn.close()

    enhanced_question = question
    if context_parts:
        context = " | ".join(context_parts)
        system_prefix = (
            "[SYSTEM: You are Teen Zen Assistant, a clinical AI helping a licensed therapist. "
            "You have access to the following patient data:\n\n"
        )
        system_suffix = (
            "\n\nINSTRUCTIONS:\n"
            "- Answer questions about this patient using the data above. If the data contains the answer, provide it directly.\n"
            "- For profile questions (age, name, etc.), check Patient Profile.\n"
            "- For behavioral patterns, check Chat History and Key Topics.\n"
            "- For clinical questions, check Clinical Data and Assigned Tasks.\n"
            "- If info is NOT in the data, say so and suggest the therapist ask the patient or update intake forms.\n"
            "- You may also answer general knowledge questions to assist the therapist.\n"
            "- Be professional, concise, and clinically relevant.]\n\n"
        )
        # Truncate context to fit model's 2048 token window (~1500 chars for context)
        if len(context) > 1500:
            context = context[:1500] + "..."
        enhanced_question = system_prefix + context + system_suffix + "Therapist question: " + question

    async def event_generator():
        try:
            logger.info(f"🔍 [Provider Stream] Q: {question} | Patient: {patient_id}")
            if chain_v2.rag_chain is None:
                yield f"data: {json.dumps({'type': 'error', 'message': 'RAG system not initialized'})}\n\n"
                return

            # Intercept time/weather questions for provider too
            if detect_time_question(question):
                answer = get_current_time_response()
                yield f"data: {json.dumps({'type': 'token', 'text': answer})}\n\n"
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                return
            if detect_weather_question(question):
                answer = get_weather_response()
                yield f"data: {json.dumps({'type': 'token', 'text': answer})}\n\n"
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                return

            for token in chain_v2.rag_chain.stream(enhanced_question):
                yield f"data: {json.dumps({'type': 'token', 'text': token})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        except Exception as e:
            logger.error(f"💥 [Provider Stream] Error: {str(e)}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    return StreamingResponse(event_generator(), media_type="text/event-stream")