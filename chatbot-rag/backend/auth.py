from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import JWTError, jwt
from typing import Optional
from db import get_db_connection, dict_cursor
import psycopg2
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

MAX_PATIENTS_PER_PROVIDER = 15


def get_db_connection():
    """Get PostgreSQL connection."""
    from db import get_db_connection as _get_conn
    return _get_conn()


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

        # Auto-assign to a provider if this is a user (patient)
        if role == 'user':
            try:
                auto_assign_patient(user_id)
            except Exception as e:
                print(f"⚠️ Auto-assign failed: {e}")

        return {"id": user_id, "username": username, "email": email, "role": role, "email_sent": email_sent}
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
    cursor.execute('SELECT verification_token, pin_expires_at FROM users WHERE email = %s AND email_verified = 0', (email,))
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
    cursor.execute('UPDATE users SET email_verified = 1, verification_token = NULL, pin_expires_at = NULL WHERE email = %s', (email,))
    conn.commit()
    conn.close()
    return True


def resend_verification_pin(email: str) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT username, email_verified FROM users WHERE email = %s', (email,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise ValueError("Email not found")
    if row['email_verified']:
        conn.close()
        raise ValueError("Email is already verified")
    new_pin = generate_pin()
    pin_expires = (datetime.utcnow() + timedelta(minutes=10)).isoformat()
    cursor.execute('UPDATE users SET verification_token = %s, pin_expires_at = %s WHERE email = %s', (new_pin, pin_expires, email))
    conn.commit()
    conn.close()
    return send_verification_email(email, new_pin, row['username'])


def get_user_by_email(email: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None


def get_user_by_id(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))
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
    cursor.execute('UPDATE users SET last_login = %s WHERE id = %s', (datetime.utcnow(), user['id']))
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
            "email": payload.get("email"), "name": payload.get("name", ""),
            "given_name": payload.get("given_name", ""), "picture": payload.get("picture", ""),
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
        cursor.execute('UPDATE users SET last_login = %s WHERE id = %s', (datetime.utcnow(), user['id']))
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
        cursor.execute('SELECT id FROM users WHERE username = %s', (username,))
        if not cursor.fetchone():
            break
        username = f"{base_username}{counter}"
        counter += 1
    random_password = secrets.token_urlsafe(32)
    password_hash = hash_password(random_password)
    cursor.execute('INSERT INTO users (username, email, password_hash, role, email_verified) VALUES (%s, %s, %s, \'user\', 1)', (username, email, password_hash))
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()
    # Auto-assign
    try:
        auto_assign_patient(user_id)
    except Exception as e:
        print(f"⚠️ Auto-assign failed: {e}")
    return {"id": user_id, "username": username, "email": email, "role": "user", "email_verified": 1}


def verify_email_token(token: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET email_verified = 1, verification_token = NULL WHERE verification_token = %s', (token,))
    rows_affected = cursor.rowcount
    conn.commit()
    conn.close()
    return rows_affected > 0


# ========== QUARTER HELPERS ==========

def get_quarter_dates(year: int, quarter: int):
    quarter_starts = {1: "01-01", 2: "04-01", 3: "07-01", 4: "10-01"}
    quarter_ends = {1: "03-31", 2: "06-30", 3: "09-30", 4: "12-31"}
    return f"{year}-{quarter_starts[quarter]}", f"{year}-{quarter_ends[quarter]}"


def get_current_quarter():
    now = datetime.utcnow()
    return now.year, (now.month - 1) // 3 + 1


# ========== CHAT HISTORY ==========

def save_chat_message(user_id: int, role: str, text: str, sources: str = None, timing: float = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO chat_messages (user_id, role, text, sources, timing) VALUES (%s, %s, %s, %s, %s)',
                   (user_id, role, text, sources, timing))
    conn.commit()
    conn.close()


def get_chat_history(user_id: int, year: int = None, quarter: int = None):
    if year is None or quarter is None:
        year, quarter = get_current_quarter()
    start_date, end_date = get_quarter_dates(year, quarter)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT role, text, sources, timing, created_at FROM chat_messages
        WHERE user_id = ? AND hidden = 0 AND date(created_at) >= ? AND date(created_at) <= ?
        ORDER BY created_at ASC
    ''', (user_id, start_date, end_date))
    rows = cursor.fetchall()
    conn.close()
    messages = []
    for row in rows:
        msg = {"type": row['role'], "text": row['text'], "timing": row['timing'], "created_at": row['created_at']}
        if row['sources']:
            try: msg['sources'] = json.loads(row['sources'])
            except: msg['sources'] = []
        else:
            msg['sources'] = []
        messages.append(msg)
    return messages


def get_available_quarters(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT DISTINCT strftime('%Y', created_at) as year,
            CASE WHEN cast(strftime('%m', created_at) as integer) <= 3 THEN 1
                 WHEN cast(strftime('%m', created_at) as integer) <= 6 THEN 2
                 WHEN cast(strftime('%m', created_at) as integer) <= 9 THEN 3
                 ELSE 4 END as quarter, COUNT(*) as count
        FROM chat_messages WHERE user_id = ?
        GROUP BY year, quarter ORDER BY year DESC, quarter DESC
    ''', (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [{"year": int(r['year']), "quarter": int(r['quarter']), "count": r['count']} for r in rows]


def clear_chat_history(user_id: int):
    year, quarter = get_current_quarter()
    start_date, end_date = get_quarter_dates(year, quarter)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE chat_messages SET hidden = 1 WHERE user_id = %s AND date(created_at) >= %s AND date(created_at) <= %s',
                   (user_id, start_date, end_date))
    conn.commit()
    conn.close()


def get_chat_history_for_archive(user_id: int, year: int, quarter: int):
    start_date, end_date = get_quarter_dates(year, quarter)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT role, text, sources, timing, created_at FROM chat_messages
        WHERE user_id = ? AND date(created_at) >= ? AND date(created_at) <= ?
        ORDER BY created_at ASC
    ''', (user_id, start_date, end_date))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def create_archive_record(user_id: int, provider_id: int, quarter: int, year: int, message_count: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO chat_archives (user_id, provider_id, quarter, year, message_count) VALUES (%s, %s, %s, %s, %s)',
                   (user_id, provider_id, f"Q{quarter}", year, message_count))
    conn.commit()
    archive_id = cursor.lastrowid
    conn.close()
    return archive_id


def get_archives_for_provider(provider_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT ca.*, u.username as user_name, u.email as user_email
        FROM chat_archives ca JOIN users u ON ca.user_id = u.id
        WHERE ca.provider_id = ? ORDER BY ca.year DESC, ca.quarter DESC
    ''', (provider_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_provider_for_user(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT provider_id FROM provider_patients WHERE user_id = %s LIMIT 1', (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row['provider_id'] if row else None


def get_provider_info_for_user(user_id: int):
    """Get the provider's name/email for a given patient"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT u.id, u.username, u.email, u.profile_pic
        FROM provider_patients pp
        JOIN users u ON u.id = pp.provider_id
        WHERE pp.user_id = ?
        LIMIT 1
    ''', (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {'id': row['id'], 'username': row['username'], 'email': row['email'], 'profile_pic': row['profile_pic']}
    return None


# ========== PROVIDER-PATIENT MANAGEMENT ==========

def auto_assign_patient(user_id: int):
    """Auto-assign a new user to a provider with fewer than MAX patients"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if already assigned
    cursor.execute('SELECT id FROM provider_patients WHERE user_id = %s', (user_id,))
    if cursor.fetchone():
        conn.close()
        return  # Already assigned

    # Find providers with capacity, sorted by fewest patients
    cursor.execute('''
        SELECT u.id, COUNT(pp.id) as patient_count
        FROM users u
        LEFT JOIN provider_patients pp ON u.id = pp.provider_id
        WHERE u.role = 'provider' AND u.email_verified = 1
        GROUP BY u.id
        HAVING patient_count < ?
        ORDER BY patient_count ASC
        LIMIT 1
    ''', (MAX_PATIENTS_PER_PROVIDER,))
    row = cursor.fetchone()

    if row:
        cursor.execute('INSERT OR IGNORE INTO provider_patients (provider_id, user_id) VALUES (%s, %s)',
                       (row['id'], user_id))
        conn.commit()
        print(f"✅ Auto-assigned user {user_id} to provider {row['id']}")
    else:
        print(f"⚠️ No available providers for user {user_id}")

    conn.close()


def assign_patient_to_provider(provider_id: int, user_id: int):
    """Manually assign a patient to a provider"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check capacity
    cursor.execute('SELECT COUNT(*) as cnt FROM provider_patients WHERE provider_id = %s', (provider_id,))
    count = cursor.fetchone()['cnt']
    if count >= MAX_PATIENTS_PER_PROVIDER:
        conn.close()
        raise ValueError(f"Provider has reached maximum of {MAX_PATIENTS_PER_PROVIDER} patients")

    try:
        cursor.execute('INSERT INTO provider_patients (provider_id, user_id) VALUES (%s, %s)', (provider_id, user_id))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise ValueError("Patient already assigned to this provider")
    conn.close()


def remove_patient_from_provider(provider_id: int, user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM provider_patients WHERE provider_id = %s AND user_id = %s', (provider_id, user_id))
    conn.commit()
    conn.close()


def get_provider_patients(provider_id: int):
    """Get all patients assigned to a provider"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT u.id, u.username, u.email, u.age, u.created_at, u.last_login, u.profile_pic, pp.assigned_at
        FROM provider_patients pp
        JOIN users u ON pp.user_id = u.id
        WHERE pp.provider_id = ?
        ORDER BY u.username ASC
    ''', (provider_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_patient_count(provider_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) as cnt FROM provider_patients WHERE provider_id = %s', (provider_id,))
    count = cursor.fetchone()['cnt']
    conn.close()
    return count


# ========== CLINICAL INTAKE ==========

def save_clinical_intake(user_id: int, provider_id: int, intake_data: dict):
    conn = get_db_connection()
    cursor = conn.cursor()
    data_json = json.dumps(intake_data)
    now = datetime.utcnow().isoformat()
    cursor.execute('''
        INSERT INTO patient_clinical_data (user_id, provider_id, intake_data, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id, provider_id)
        DO UPDATE SET intake_data = ?, updated_at = ?
    ''', (user_id, provider_id, data_json, now, data_json, now))
    conn.commit()
    conn.close()


def get_clinical_intake(user_id: int, provider_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT intake_data, updated_at FROM patient_clinical_data WHERE user_id = %s AND provider_id = %s',
                   (user_id, provider_id))
    row = cursor.fetchone()
    conn.close()
    if row:
        try:
            return {"data": json.loads(row['intake_data']), "updated_at": row['updated_at']}
        except:
            return {"data": {}, "updated_at": row['updated_at']}
    return {"data": {}, "updated_at": None}


# ========== THERAPIST OBSERVATIONS (PRIVATE) ==========

def save_therapist_observations(user_id: int, provider_id: int, observations: dict):
    conn = get_db_connection()
    cursor = conn.cursor()
    obs_json = json.dumps(observations)
    now = datetime.utcnow().isoformat()
    cursor.execute('''
        INSERT INTO therapist_observations (user_id, provider_id, observations, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id, provider_id)
        DO UPDATE SET observations = ?, updated_at = ?
    ''', (user_id, provider_id, obs_json, now, obs_json, now))
    conn.commit()
    conn.close()


def get_therapist_observations(user_id: int, provider_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT observations, updated_at FROM therapist_observations WHERE user_id = %s AND provider_id = %s',
                   (user_id, provider_id))
    row = cursor.fetchone()
    conn.close()
    if row:
        try:
            return {"data": json.loads(row['observations']), "updated_at": row['updated_at']}
        except:
            return {"data": {}, "updated_at": row['updated_at']}
    return {"data": {}, "updated_at": None}


# ========== TASKS ==========

def create_task(title: str, description: str, assigned_by: int, assigned_to: int, due_date: str = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO tasks (title, description, assigned_by, assigned_to, due_date) VALUES (%s, %s, %s, %s, %s)',
                   (title, description, assigned_by, assigned_to, due_date))
    conn.commit()
    task_id = cursor.lastrowid
    conn.close()
    return task_id


def get_tasks_for_user(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT t.*, u.username as assigned_by_name FROM tasks t
        JOIN users u ON t.assigned_by = u.id WHERE t.assigned_to = ? ORDER BY t.created_at DESC
    ''', (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_tasks_assigned_by(provider_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT t.*, u.username as assigned_to_name FROM tasks t
        JOIN users u ON t.assigned_to = u.id WHERE t.assigned_by = ? ORDER BY t.created_at DESC
    ''', (provider_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def update_task_status(task_id: int, user_id: int, status: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    completed_at = datetime.utcnow().isoformat() if status == 'completed' else None
    cursor.execute('UPDATE tasks SET status = %s, completed_at = %s WHERE id = %s AND assigned_to = %s',
                   (status, completed_at, task_id, user_id))
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


# ========== FORGOT PASSWORD ==========

def send_reset_pin(email: str) -> bool:
    """Send a password reset PIN to the user's email"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, username, email_verified FROM users WHERE email = %s', (email,))
    user = cursor.fetchone()
    if not user:
        conn.close()
        raise ValueError("No account found with that email address")
    if not user['email_verified']:
        conn.close()
        raise ValueError("Email not yet verified. Please verify your email first.")

    pin = generate_pin()
    pin_expires = (datetime.utcnow() + timedelta(minutes=15)).isoformat()
    cursor.execute('UPDATE users SET verification_token = %s, pin_expires_at = %s WHERE email = %s',
                   (f"RESET:{pin}", pin_expires, email))
    conn.commit()
    conn.close()

    # Send reset email
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        print(f"⚠️ Gmail not configured. Reset PIN for {email}: {pin}")
        return True
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🔑 Password Reset Code: {pin}"
        msg["From"] = f"RAG Chatbot <{GMAIL_ADDRESS}>"
        msg["To"] = email
        html_body = f"""
        <div style="font-family: -apple-system, sans-serif; max-width: 480px; margin: 0 auto; padding: 40px 20px;">
            <div style="text-align: center; margin-bottom: 32px;">
                <h1 style="margin: 0; font-size: 24px; color: #18181b;">Reset Your Password</h1>
                <p style="margin: 8px 0 0; color: #71717a; font-size: 14px;">Hey {user['username']}, use this code to reset your password.</p>
            </div>
            <div style="background: #18181b; border-radius: 16px; padding: 32px; text-align: center;">
                <p style="margin: 0 0 12px; color: #a1a1aa; font-size: 12px; text-transform: uppercase; letter-spacing: 2px;">Your reset code</p>
                <div style="font-size: 36px; font-weight: bold; letter-spacing: 8px; color: #f59e0b; font-family: monospace;">{pin}</div>
                <p style="margin: 16px 0 0; color: #52525b; font-size: 12px;">This code expires in 15 minutes</p>
            </div>
        </div>
        """
        msg.attach(MIMEText(html_body, "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_ADDRESS, email, msg.as_string())
        return True
    except Exception as e:
        print(f"❌ Failed to send reset email: {e}")
        return False


def verify_reset_and_change_password(email: str, pin: str, new_password: str) -> bool:
    """Verify reset PIN and change the password"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT verification_token, pin_expires_at FROM users WHERE email = %s', (email,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False

    stored_token = row['verification_token']
    expires_at = row['pin_expires_at']

    if not stored_token or not stored_token.startswith("RESET:"):
        conn.close()
        raise ValueError("No reset request found. Please request a new code.")
    if expires_at and datetime.utcnow() > datetime.fromisoformat(expires_at):
        conn.close()
        raise ValueError("Reset code has expired. Please request a new one.")

    stored_pin = stored_token.replace("RESET:", "")
    if stored_pin != pin:
        conn.close()
        return False

    # Reset password
    new_hash = hash_password(new_password)
    cursor.execute('UPDATE users SET password_hash = %s, verification_token = NULL, pin_expires_at = NULL WHERE email = %s',
                   (new_hash, email))
    conn.commit()
    conn.close()
    return True


# ========== KNOWLEDGE GRAPH EXTRACTION ==========

THERAPY_TOPICS = {
    'anxiety': ['anxiety', 'anxious', 'worry', 'worried', 'nervous', 'panic', 'fear', 'scared', 'tense', 'overthinking', 'restless'],
    'depression': ['depression', 'depressed', 'sad', 'hopeless', 'empty', 'numb', 'unmotivated', 'worthless', 'helpless', 'melancholy'],
    'self-esteem': ['self-esteem', 'confidence', 'self-worth', 'insecure', 'inadequate', 'not good enough', 'imposter', 'self-doubt'],
    'relationships': ['relationship', 'partner', 'boyfriend', 'girlfriend', 'spouse', 'dating', 'breakup', 'love', 'trust', 'intimacy', 'commitment'],
    'family': ['family', 'parent', 'mother', 'father', 'mom', 'dad', 'sibling', 'brother', 'sister', 'child', 'children', 'son', 'daughter'],
    'anger': ['anger', 'angry', 'frustrated', 'rage', 'irritated', 'resentment', 'furious', 'hostile', 'annoyed'],
    'grief': ['grief', 'loss', 'mourning', 'death', 'bereavement', 'missing', 'passed away', 'gone'],
    'trauma': ['trauma', 'ptsd', 'flashback', 'nightmares', 'abuse', 'assault', 'accident', 'violence', 'trigger'],
    'stress': ['stress', 'stressed', 'overwhelmed', 'burnout', 'exhausted', 'pressure', 'overworked', 'tension'],
    'sleep': ['sleep', 'insomnia', 'tired', 'fatigue', 'nightmares', 'restless', 'awake', 'sleeping'],
    'work': ['work', 'job', 'career', 'boss', 'coworker', 'workplace', 'fired', 'promotion', 'office', 'employed', 'unemployed'],
    'school': ['school', 'college', 'university', 'grades', 'exam', 'homework', 'teacher', 'student', 'class', 'study', 'academic'],
    'loneliness': ['lonely', 'alone', 'isolated', 'no friends', 'disconnected', 'withdrawn', 'solitude'],
    'substance use': ['alcohol', 'drinking', 'drugs', 'marijuana', 'cannabis', 'smoking', 'vaping', 'substance', 'addiction', 'sober'],
    'self-harm': ['self-harm', 'cutting', 'hurting myself', 'self-injury'],
    'eating': ['eating', 'food', 'appetite', 'weight', 'body image', 'anorexia', 'bulimia', 'binge'],
    'social': ['social', 'friends', 'peer', 'bullying', 'fitting in', 'acceptance', 'rejection', 'popularity'],
    'identity': ['identity', 'who am i', 'purpose', 'meaning', 'values', 'beliefs', 'sexuality', 'gender'],
    'coping': ['coping', 'cope', 'manage', 'strategy', 'technique', 'breathing', 'meditation', 'mindfulness', 'journal'],
    'growth': ['growth', 'progress', 'better', 'improve', 'goal', 'hope', 'change', 'healing', 'recovery', 'strength'],
    'communication': ['communication', 'express', 'boundaries', 'assertive', 'listen', 'conflict', 'argument', 'misunderstand'],
    'finances': ['money', 'financial', 'debt', 'bills', 'afford', 'rent', 'broke', 'income'],
}


# ========== PROFILE PICTURE (Backend Storage) ==========

def save_profile_pic(user_id: int, pic_data: str):
    """Save base64 profile picture to database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET profile_pic = %s WHERE id = %s', (pic_data, user_id))
    conn.commit()
    conn.close()

def get_profile_pic(user_id: int):
    """Get profile picture for a user"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT profile_pic FROM users WHERE id = %s', (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row['profile_pic'] if row else None


def extract_knowledge_graph(user_id: int):
    """Extract a knowledge graph from a patient's chat messages"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT text, role, created_at FROM chat_messages WHERE user_id = %s ORDER BY created_at ASC", (user_id,))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return {"nodes": [], "edges": [], "stats": {}}

    # Count topic occurrences and co-occurrences
    topic_counts = {}
    topic_cooccurrence = {}
    topic_timeline = {}
    message_count = 0

    for row in rows:
        text = row['text'].lower()
        role = row['role']
        created_at = row['created_at'][:10] if row['created_at'] else ''

        # Only analyze user messages for the graph (their own words)
        if role != 'user':
            continue

        message_count += 1
        found_topics = set()

        for topic, keywords in THERAPY_TOPICS.items():
            for kw in keywords:
                if kw in text:
                    found_topics.add(topic)
                    break

        for t in found_topics:
            topic_counts[t] = topic_counts.get(t, 0) + 1
            if t not in topic_timeline:
                topic_timeline[t] = []
            topic_timeline[t].append(created_at)

        # Co-occurrences (topics mentioned in same message)
        topics_list = sorted(found_topics)
        for i in range(len(topics_list)):
            for j in range(i + 1, len(topics_list)):
                pair = (topics_list[i], topics_list[j])
                topic_cooccurrence[pair] = topic_cooccurrence.get(pair, 0) + 1

    # Build nodes
    nodes = []
    if topic_counts:
        max_count = max(topic_counts.values())
        # Add patient center node
        nodes.append({
            "id": "patient",
            "label": "Patient",
            "size": 30,
            "color": "#818cf8",
            "type": "center"
        })

        for topic, count in sorted(topic_counts.items(), key=lambda x: -x[1]):
            size = 10 + (count / max_count) * 25
            # Color by category
            if topic in ('self-harm', 'trauma', 'substance use'):
                color = "#ef4444"  # red
            elif topic in ('anxiety', 'depression', 'anger', 'grief', 'stress'):
                color = "#f59e0b"  # amber
            elif topic in ('growth', 'coping', 'strengths'):
                color = "#22c55e"  # green
            else:
                color = "#6366f1"  # indigo
            nodes.append({
                "id": topic,
                "label": topic.replace('-', ' ').title(),
                "size": size,
                "color": color,
                "count": count,
                "type": "topic",
                "first_seen": topic_timeline[topic][0] if topic_timeline.get(topic) else '',
                "last_seen": topic_timeline[topic][-1] if topic_timeline.get(topic) else '',
            })

    # Build edges
    edges = []
    # Connect all topics to center
    for topic in topic_counts:
        edges.append({
            "source": "patient",
            "target": topic,
            "weight": topic_counts[topic],
            "type": "primary"
        })

    # Add co-occurrence edges
    for (t1, t2), count in sorted(topic_cooccurrence.items(), key=lambda x: -x[1]):
        if count >= 1:
            edges.append({
                "source": t1,
                "target": t2,
                "weight": count,
                "type": "cooccurrence"
            })

    # Stats
    stats = {
        "total_messages": message_count,
        "topics_found": len(topic_counts),
        "top_topics": sorted(topic_counts.items(), key=lambda x: -x[1])[:5],
        "strongest_connections": sorted(
            [(f"{t1} ↔ {t2}", c) for (t1, t2), c in topic_cooccurrence.items()],
            key=lambda x: -x[1]
        )[:5]
    }

    return {"nodes": nodes, "edges": edges, "stats": stats}