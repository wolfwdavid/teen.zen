from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import JWTError, jwt
from typing import Optional
import json
import os
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Password hashing
pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')

# JWT settings
SECRET_KEY = 'your-secret-key-change-this-in-production-make-it-very-long-and-random'
ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Simple file-based user storage
USERS_FILE = 'users.json'
VERIFICATION_CODES_FILE = 'verification_codes.json'

# Email settings (configure these in .env)
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USERNAME = os.getenv('SMTP_USERNAME', '')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
FROM_EMAIL = os.getenv('FROM_EMAIL', SMTP_USERNAME)

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)

def load_verification_codes():
    if os.path.exists(VERIFICATION_CODES_FILE):
        with open(VERIFICATION_CODES_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_verification_codes(codes):
    with open(VERIFICATION_CODES_FILE, 'w') as f:
        json.dump(codes, f, indent=2)

def cleanup_expired_codes():
    codes = load_verification_codes()
    now = datetime.now()
    
    # Remove expired codes
    expired_emails = []
    for email, data in codes.items():
        expiry = datetime.fromisoformat(data['expires_at'])
        if now > expiry:
            expired_emails.append(email)
    
    for email in expired_emails:
        del codes[email]
    
    if expired_emails:
        save_verification_codes(codes)

def generate_verification_code(email: str) -> str:
    # Clean up expired codes first
    cleanup_expired_codes()
    
    # Generate 6-digit code
    code = str(random.randint(100000, 999999))
    
    # Store with 5-minute expiry
    codes = load_verification_codes()
    codes[email] = {
        'code': code,
        'created_at': datetime.now().isoformat(),
        'expires_at': (datetime.now() + timedelta(minutes=5)).isoformat()
    }
    save_verification_codes(codes)
    
    return code

def verify_code(email: str, code: str) -> bool:
    cleanup_expired_codes()
    
    codes = load_verification_codes()
    if email not in codes:
        return False
    
    stored_data = codes[email]
    
    # Check if code matches
    if stored_data['code'] != code:
        return False
    
    # Check if expired
    expiry = datetime.fromisoformat(stored_data['expires_at'])
    if datetime.now() > expiry:
        del codes[email]
        save_verification_codes(codes)
        return False
    
    # Code is valid - remove it (one-time use)
    del codes[email]
    save_verification_codes(codes)
    return True

def send_verification_email(email: str, code: str) -> bool:
    if not SMTP_USERNAME or not SMTP_PASSWORD:
        print(f'[DEV MODE] Verification code for {email}: {code}')
        return True
    
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'Your Teen.zen Verification Code'
        msg['From'] = FROM_EMAIL
        msg['To'] = email
        
        text = f'''
Your Teen.zen verification code is: {code}

This code will expire in 5 minutes.

If you didn't request this code, please ignore this email.

- The Teen.zen Team
        '''
        
        html = f'''
        <html>
          <body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f5f5f5;">
            <div style="max-width: 600px; margin: 0 auto; background: white; padding: 40px; border-radius: 10px;">
              <h1 style="color: #667eea; text-align: center;">Teen.zen</h1>
              <h2 style="color: #333;">Your Verification Code</h2>
              <div style="background: #f0f0f0; padding: 20px; border-radius: 5px; text-align: center; margin: 20px 0;">
                <h1 style="color: #667eea; font-size: 36px; letter-spacing: 8px; margin: 0;">{code}</h1>
              </div>
              <p style="color: #666;">This code will expire in <strong>5 minutes</strong>.</p>
              <p style="color: #999; font-size: 14px;">If you didn't request this code, please ignore this email.</p>
              <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
              <p style="color: #999; font-size: 12px; text-align: center;">© 2026 Teen.zen - Your Mental Health Companion</p>
            </div>
          </body>
        </html>
        '''
        
        part1 = MIMEText(text, 'plain')
        part2 = MIMEText(html, 'html')
        msg.attach(part1)
        msg.attach(part2)
        
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
        
        return True
    except Exception as e:
        print(f'Failed to send email: {e}')
        return False

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_user(email: str, password: str, role: str = 'user'):
    users = load_users()
    
    if email in users:
        return None
    
    users[email] = {
        'email': email,
        'hashed_password': get_password_hash(password),
        'role': role,
        'created_at': datetime.now().isoformat(),
        'verified': True  # Set to True after code verification
    }
    
    save_users(users)
    return {'email': email, 'role': role}

def authenticate_user(email: str, password: str):
    users = load_users()
    
    if email not in users:
        return None
    
    user = users[email]
    if not verify_password(password, user['hashed_password']):
        return None
    
    return {'email': email, 'role': user['role']}

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({'exp': expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt