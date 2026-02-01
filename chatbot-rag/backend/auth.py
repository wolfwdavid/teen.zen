from passlib.context import CryptContext
import json
import os
import random
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# --- 1. APP INITIALIZATION & CORS ---
app = FastAPI()

# Added port 5174 and 5175 to cover both common Svelte/Vite ports
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5175", "http://localhost:5174"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 2. AUTH SETTINGS ---
# Initialize CryptContext here to fix the NameError
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = "your-secret-key-change-this-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
USERS_FILE = "users.json"

# Temporary storage for verification codes
verification_codes = {}

# --- 3. VERIFICATION HELPERS ---

def generate_verification_code(email: str = None):
    return str(random.randint(100000, 999999))

def send_verification_email(email: str, code: str):
    verification_codes[email] = code
    print(f"\n[EMAIL SIMULATION] To: {email} | Code: {code}\n")
    return True

def verify_code(email: str, code: str):
    stored_code = verification_codes.get(email)
    if stored_code and stored_code == code:
        del verification_codes[email]
        return True
    return False

# --- 4. PASSWORD HELPERS (UPDATED) ---

def get_password_hash(password: str) -> str:
    """Uses pwd_context to hash the password."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Uses pwd_context to verify the password."""
    return pwd_context.verify(plain_password, hashed_password)

# --- 5. DATA PERSISTENCE ---

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)

# --- 6. CORE AUTH LOGIC ---

def create_user(email: str, password: str, role: str = "user"):
    users = load_users()
    if email in users:
        return None
    
    users[email] = {
        "email": email,
        "hashed_password": get_password_hash(password),
        "role": role,
        "created_at": datetime.now().isoformat()
    }
    save_users(users)
    return {"email": email, "role": role}

def authenticate_user(email: str, password: str):
    users = load_users()
    if email not in users:
        return None
    
    user = users[email]
    if not verify_password(password, user["hashed_password"]):
        return None
    return {"email": email, "role": user["role"]}

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)