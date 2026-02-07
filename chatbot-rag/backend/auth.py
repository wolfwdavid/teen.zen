from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import JWTError, jwt
from typing import Optional
import sqlite3
from pathlib import Path
import secrets
import hashlib
import base64

# Configuration
SECRET_KEY = "JWT_SECRET", "fallback-key-for-dev"  # Change this!
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
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
    """Create a new user with email verification token"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        password_hash = hash_password(password)
        verification_token = secrets.token_urlsafe(32)

        cursor.execute('''
            INSERT INTO users (username, email, password_hash, age, phone, verification_token)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (username, email, password_hash, age, phone, verification_token))

        conn.commit()
        user_id = cursor.lastrowid
        conn.close()

        return {
            "id": user_id,
            "username": username,
            "email": email,
            "verification_token": verification_token
        }
    except sqlite3.IntegrityError as e:
        conn.close()
        if "username" in str(e):
            raise ValueError("Username already exists")
        elif "email" in str(e):
            raise ValueError("Email already exists")
        raise ValueError("User creation failed")


def get_user_by_email(email: str):
    """Get user by email"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None


def verify_email_token(token: str):
    """Verify email with token"""
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