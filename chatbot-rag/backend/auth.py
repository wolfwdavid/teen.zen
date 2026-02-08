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
    # Pre-hash to stay within bcrypt's 72-byte limit
    prehashed = base64.b64encode(hashlib.sha256(password.encode()).digest()).decode()
    return pwd_context.hash(prehashed)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    prehashed = base64.b64encode(hashlib.sha256(plain_password.encode()).digest()).decode()
    return pwd_context.verify(prehashed, hashed_password)


def generate_pin() -> str:
    """Generate a 6-digit verification PIN"""
    return str(random.randint(100000, 999999))


def send_verification_email(to_email: str, pin: str, username: str) -> bool:
    """Send verification PIN via Gmail SMTP"""
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        print(f"⚠️ Gmail not configured. Verification PIN for {to_email}: {pin}")
        return True  # Return True so registration still works in dev mode

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🔐 Your Verification Code: {pin}"
        msg["From"] = f"RAG Chatbot <{GMAIL_ADDRESS}>"
        msg["To"] = to_email

        html_body = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 480px; margin: 0 auto; padding: 40px 20px;">
            <div style="text-align: center; margin-bottom: 32px;">
                <div style="display: inline-block; background: #4f46e5; border-radius: 12px; padding: 12px; margin-bottom: 16px;">
                    <span style="font-size: 24px; color: white;">🤖</span>
                </div>
                <h1 style="margin: 0; font-size: 24px; color: #18181b;">Verify Your Email</h1>
                <p style="margin: 8px 0 0; color: #71717a; font-size: 14px;">Hey {username}, welcome to RAG Chatbot Pro!</p>
            </div>
            
            <div style="background: #18181b; border-radius: 16px; padding: 32px; text-align: center; margin-bottom: 24px;">
                <p style="margin: 0 0 12px; color: #a1a1aa; font-size: 12px; text-transform: uppercase; letter-spacing: 2px;">Your verification code</p>
                <div style="font-size: 36px; font-weight: bold; letter-spacing: 8px; color: #818cf8; font-family: monospace;">{pin}</div>
                <p style="margin: 16px 0 0; color: #52525b; font-size: 12px;">This code expires in 10 minutes</p>
            </div>
            
            <p style="text-align: center; color: #52525b; font-size: 12px; margin: 0;">
                If you didn't create an account, you can safely ignore this email.
            </p>
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
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_user(username: str, email: str, password: str, age: Optional[int] = None, phone: Optional[str] = None):
    """Create a new user with email verification PIN"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        password_hash = hash_password(password)
        pin = generate_pin()
        pin_expires = (datetime.utcnow() + timedelta(minutes=10)).isoformat()

        cursor.execute('''
            INSERT INTO users (username, email, password_hash, age, phone, verification_token, pin_expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (username, email, password_hash, age, phone, pin, pin_expires))

        conn.commit()
        user_id = cursor.lastrowid
        conn.close()

        # Send verification email
        email_sent = send_verification_email(email, pin, username)

        return {
            "id": user_id,
            "username": username,
            "email": email,
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
    """Verify email with 6-digit PIN"""
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

    # Check expiration
    if expires_at and datetime.utcnow() > datetime.fromisoformat(expires_at):
        conn.close()
        raise ValueError("Verification code has expired. Please request a new one.")

    if stored_pin != pin:
        conn.close()
        return False

    cursor.execute('''
        UPDATE users 
        SET email_verified = 1, verification_token = NULL, pin_expires_at = NULL
        WHERE email = ?
    ''', (email,))

    conn.commit()
    conn.close()
    return True


def resend_verification_pin(email: str) -> bool:
    """Generate a new PIN and resend verification email"""
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
    """Get user by email"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None


def verify_email_token(token: str):
    """Verify email with token (legacy support)"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE users 
        SET email_verified = 1, verification_token = NULL
        WHERE verification_token = ?
    ''', (token,))

    rows_affected = cursor.rowcount
    conn.commit()
    conn.close()

    return rows_affected > 0


def authenticate_user(email: str, password: str):
    """Authenticate user and return user data"""
    user = get_user_by_email(email)
    if not user:
        return None
    if not verify_password(password, user['password_hash']):
        return None

    # Update last login
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE users SET last_login = ? WHERE id = ?
    ''', (datetime.utcnow(), user['id']))
    conn.commit()
    conn.close()

    return user


def verify_google_token(token: str):
    """Verify Google OAuth token and return user info"""
    try:
        # Verify token with Google
        resp = http_requests.get(
            f"https://oauth2.googleapis.com/tokeninfo?id_token={token}"
        )
        
        if resp.status_code != 200:
            raise ValueError("Invalid Google token")
        
        payload = resp.json()
        
        # Verify the token is for our app
        if payload.get('aud') != GOOGLE_CLIENT_ID:
            raise ValueError("Token not intended for this app")
        
        # Check email is verified by Google
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
    """Get existing user or create new one from Google sign-in"""
    email = google_info['email']
    
    # Check if user exists
    user = get_user_by_email(email)
    
    if user:
        # Update last login
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users SET last_login = ? WHERE id = ?
        ''', (datetime.utcnow(), user['id']))
        conn.commit()
        conn.close()
        return user
    
    # Create new user from Google info
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Generate username from name or email
    username = google_info.get('given_name', '').lower() or email.split('@')[0]
    # Make username alphanumeric
    username = ''.join(c for c in username if c.isalnum())
    
    # Ensure username is unique
    base_username = username
    counter = 1
    while True:
        cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
        if not cursor.fetchone():
            break
        username = f"{base_username}{counter}"
        counter += 1
    
    # Create user with a random password (they'll sign in via Google)
    random_password = secrets.token_urlsafe(32)
    password_hash = hash_password(random_password)
    
    cursor.execute('''
        INSERT INTO users (username, email, password_hash, email_verified)
        VALUES (?, ?, ?, 1)
    ''', (username, email, password_hash))
    
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()
    
    return {
        "id": user_id,
        "username": username,
        "email": email,
        "email_verified": 1
    }