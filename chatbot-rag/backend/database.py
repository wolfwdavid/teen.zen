import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent / "users.db"

def init_db():
    """Initialize the database with users table"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            age INTEGER,
            phone TEXT,
            email_verified BOOLEAN DEFAULT 0,
            verification_token TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Database initialized")

if __name__ == "__main__":
    init_db()
