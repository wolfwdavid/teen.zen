from passlib.context import CryptContext
import json
import os
import random
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from dotenv import load_dotenv

# Load variables from .env file if it exists
load_dotenv()

# --- 1. AUTH SETTINGS ---
# Updated to use your requested fallback logic
SECRET_KEY = os.getenv("JWT_SECRET", "fallback-key-for-dev")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
USERS_FILE = "users.json"

# Initialize CryptContext for secure password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Temporary storage for verification codes
verification_codes = {}

# --- 2. VERIFICATION HELPERS ---

def generate_verification_code(email: str = None):
    """Generates a random 6-digit code."""
    return str(random.randint(100000, 999999))

def send_verification_email(email: str, code: str):
    """Stores the code and prints it to the terminal for development."""
    verification_codes[email] = code
    print(f"\n[EMAIL SIMULATION] To: {email} | Code: {code}\n")
    return True

def verify_code(email: str, code: str):
    """Checks if the provided code matches the one stored."""
    stored_code = verification_codes.get(email)
    if stored_code and stored_code == code:
        del verification_codes[email]
        return True
    return False

# --- 3. PASSWORD HELPERS ---

def get_password_hash(password: str) -> str:
    """Hashes a plain-text password."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain-text password against a stored hash."""
    return pwd_context.verify(plain_password, hashed_password)

# --- 4. DATA PERSISTENCE ---

def load_users():
    """Loads users from the JSON file."""
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_users(users):
    """Saves the user dictionary to the JSON file."""
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)

# --- 5. CORE AUTH LOGIC ---

def create_user(email: str, password: str, role: str = "user"):
    """Validates and saves a new user to users.json."""
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
    """Checks credentials for login."""
    users = load_users()
    if email not in users:
        return None
    
    user = users[email]
    if not verify_password(password, user["hashed_password"]):
        return None
    return {"email": email, "role": user["role"]}

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Generates a JWT token for the session."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)