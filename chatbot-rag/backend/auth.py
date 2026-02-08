from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import JWTError, jwt
from typing import Optional
import sqlite3
from pathlib import Path
import secrets
import hashlib
import base64
import smtplib
import random
import json
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import requests as http_requests

load_dotenv()

# Configuration
SECRET_KEY = os.getenv("JWT_SECRET", "fallback-key-for-dev")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
DB_PATH = Path(__file__).parent / "users.db"


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def hash_password(password: str) -> str:
    prehashed = base64.b64encode(hashlib.sha256(password.encode()).digest()).decode()
    return pwd_context.hash(prehashed)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    prehashed = base64.b64encode(hashlib.sha256(plain_password.encode()).digest()).decode()
    return pwd_context.verify(prehashed, hashed_password)


def generate_pin() -> str:
    return str(random.randint(100000, 999999))


def send_verification_email(to_email: str, pin: str, username: str) -> bool:
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        print(f"⚠️ Gmail not configured. Verification PIN for {to_email}: {pin}")
        return True

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🔐 Your Verification Code: {pin}"
        msg["From"] = f"RAG Chatbot <{GMAIL_ADDRESS}>"
        msg["To"] = to_email

        html_body = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 480px; margin: 0 auto; padding: 40px 20px;">
            <div style="text-align: center; margin-bottom: 32px;">
                <h1 style="margin: 0; font-size: 24px; color: #18181b;">Verify Your Email</h1>
                <p style="margin: 8px 0 0; color: #71717a; font-size: 14px;">Hey {username}, welcome!</p>
            </div>
            <div style="background: #18181b; border-radius: 16px; padding: 32px; text-align: center; margin-bottom: 24px;">
                <p style="margin: 0 0 12px; color: #a1a1aa; font-size: 12px; text-transform: uppercase; letter-spacing: 2px;">Your verification code</p>
                <div style="font-size: 36px; font-weight: bold; letter-spacing: 8px; color: #818cf8; font-family: monospace;">{pin}</div>
                <p style="margin: 16px 0 0; color: #52525b; font-size: 12px;">This code expires in 10 minutes</p>
            </div>
        </div>
        """

        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_ADDRESS, to_email, msg.as_string())

        print(f"✅ Verification email sent to {to_email}")
        return True
    except Exception as e:
        print(f"❌ Failed to send email to {to_email}: {e}")
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def create_user(username: str, email: str, password: str, role: str = "user", age: Optional[int] = None, phone: Optional[str] = None):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        password_hash = hash_password(password)
        pin = generate_pin()
        pin_expires = (datetime.utcnow() + timedelta(minutes=10)).isoformat()

        cursor.execute('''
            INSERT INTO users (username, email, password_hash, role, age, phone, verification_token, pin_expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (username, email, password_hash, role, age, phone, pin, pin_expires))

        conn.commit()
        user_id = cursor.lastrowid
        conn.close()

        email_sent = send_verification_email(email, pin, username)

        return {
            "id": user_id,
            "username": username,
            "email": email,
            "role": role,
            "email_sent": email_sent
        }
    except sqlite3.IntegrityError as e:
        conn.close()
        if "username" in str(e):
            raise ValueError("Username already exists")
        elif "email" in str(e):
            raise ValueError("Email already exists")
        raise ValueError("User creation failed")


def verify_email_pin(email: str, pin: str) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        'SELECT verification_token, pin_expires_at FROM users WHERE email = ? AND email_verified = 0',
        (email,)
    )
    row = cursor.fetchone()

    if not row:
        conn.close()
        return False

    stored_pin = row['verification_token']
    expires_at = row['pin_expires_at']

    if expires_at and datetime.utcnow() > datetime.fromisoformat(expires_at):
        conn.close()
        raise ValueError("Verification code has expired. Please request a new one.")

    if stored_pin != pin:
        conn.close()
        return False

    cursor.execute('''
        UPDATE users SET email_verified = 1, verification_token = NULL, pin_expires_at = NULL
        WHERE email = ?
    ''', (email,))

    conn.commit()
    conn.close()
    return True


def resend_verification_pin(email: str) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT username, email_verified FROM users WHERE email = ?', (email,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        raise ValueError("Email not found")

    if row['email_verified']:
        conn.close()
        raise ValueError("Email is already verified")

    new_pin = generate_pin()
    pin_expires = (datetime.utcnow() + timedelta(minutes=10)).isoformat()

    cursor.execute('''
        UPDATE users SET verification_token = ?, pin_expires_at = ?
        WHERE email = ?
    ''', (new_pin, pin_expires, email))

    conn.commit()
    conn.close()

    return send_verification_email(email, new_pin, row['username'])


def get_user_by_email(email: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None


def get_user_by_id(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None


def authenticate_user(email: str, password: str):
    user = get_user_by_email(email)
    if not user:
        return None
    if not verify_password(password, user['password_hash']):
        return None

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET last_login = ? WHERE id = ?', (datetime.utcnow(), user['id']))
    conn.commit()
    conn.close()

    return user


def verify_google_token(token: str):
    try:
        resp = http_requests.get(f"https://oauth2.googleapis.com/tokeninfo?id_token={token}")
        if resp.status_code != 200:
            raise ValueError("Invalid Google token")

        payload = resp.json()

        if payload.get('aud') != GOOGLE_CLIENT_ID:
            raise ValueError("Token not intended for this app")

        if payload.get('email_verified') != 'true' and payload.get('email_verified') is not True:
            raise ValueError("Google email not verified")

        return {
            "email": payload.get("email"),
            "name": payload.get("name", ""),
            "given_name": payload.get("given_name", ""),
            "picture": payload.get("picture", ""),
            "google_id": payload.get("sub")
        }
    except Exception as e:
        raise ValueError(f"Google verification failed: {str(e)}")


def get_or_create_google_user(google_info: dict):
    email = google_info['email']
    user = get_user_by_email(email)

    if user:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET last_login = ? WHERE id = ?', (datetime.utcnow(), user['id']))
        conn.commit()
        conn.close()
        return user

    conn = get_db_connection()
    cursor = conn.cursor()

    username = google_info.get('given_name', '').lower() or email.split('@')[0]
    username = ''.join(c for c in username if c.isalnum())

    base_username = username
    counter = 1
    while True:
        cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
        if not cursor.fetchone():
            break
        username = f"{base_username}{counter}"
        counter += 1

    random_password = secrets.token_urlsafe(32)
    password_hash = hash_password(random_password)

    cursor.execute('''
        INSERT INTO users (username, email, password_hash, role, email_verified)
        VALUES (?, ?, ?, 'user', 1)
    ''', (username, email, password_hash))

    conn.commit()
    user_id = cursor.lastrowid
    conn.close()

    return {
        "id": user_id,
        "username": username,
        "email": email,
        "role": "user",
        "email_verified": 1
    }


def verify_email_token(token: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET email_verified = 1, verification_token = NULL WHERE verification_token = ?', (token,))
    rows_affected = cursor.rowcount
    conn.commit()
    conn.close()
    return rows_affected > 0


# ========== CHAT HISTORY ==========

def save_chat_message(user_id: int, role: str, text: str, sources: str = None, timing: float = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO chat_messages (user_id, role, text, sources, timing)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, role, text, sources, timing))
    conn.commit()
    conn.close()


def get_chat_history(user_id: int, limit: int = 100):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT role, text, sources, timing, created_at
        FROM chat_messages
        WHERE user_id = ?
        ORDER BY created_at ASC
        LIMIT ?
    ''', (user_id, limit))
    rows = cursor.fetchall()
    conn.close()

    messages = []
    for row in rows:
        msg = {
            "type": row['role'],
            "text": row['text'],
            "timing": row['timing'],
            "created_at": row['created_at']
        }
        if row['sources']:
            try:
                msg['sources'] = json.loads(row['sources'])
            except:
                msg['sources'] = []
        else:
            msg['sources'] = []
        messages.append(msg)

    return messages


def clear_chat_history(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM chat_messages WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()


# ========== TASKS ==========

def create_task(title: str, description: str, assigned_by: int, assigned_to: int, due_date: str = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO tasks (title, description, assigned_by, assigned_to, due_date)
        VALUES (?, ?, ?, ?, ?)
    ''', (title, description, assigned_by, assigned_to, due_date))
    conn.commit()
    task_id = cursor.lastrowid
    conn.close()
    return task_id


def get_tasks_for_user(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT t.*, u.username as assigned_by_name
        FROM tasks t
        JOIN users u ON t.assigned_by = u.id
        WHERE t.assigned_to = ?
        ORDER BY t.created_at DESC
    ''', (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_tasks_assigned_by(provider_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT t.*, u.username as assigned_to_name
        FROM tasks t
        JOIN users u ON t.assigned_to = u.id
        WHERE t.assigned_by = ?
        ORDER BY t.created_at DESC
    ''', (provider_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def update_task_status(task_id: int, user_id: int, status: str):
    conn = get_db_connection()
    cursor = conn.cursor()

    completed_at = datetime.utcnow().isoformat() if status == 'completed' else None

    cursor.execute('''
        UPDATE tasks SET status = ?, completed_at = ?
        WHERE id = ? AND assigned_to = ?
    ''', (status, completed_at, task_id, user_id))

    rows = cursor.rowcount
    conn.commit()
    conn.close()
    return rows > 0


def get_all_users_for_provider():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, email, role FROM users WHERE role = 'user' AND email_verified = 1")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]