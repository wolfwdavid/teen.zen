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
            pin_expires_at TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()
    print("✅ Database initialized")


def migrate_db():
    """Add new columns if they don't exist (safe to run multiple times)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute("ALTER TABLE users ADD COLUMN pin_expires_at TEXT")
        print("✅ Added pin_expires_at column")
    except sqlite3.OperationalError:
        pass  # Column already exists

    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    migrate_db()