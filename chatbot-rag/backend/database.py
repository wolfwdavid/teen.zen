import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent / "users.db"


def init_db():
    """Initialize the database with all tables"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            age INTEGER,
            phone TEXT,
            email_verified BOOLEAN DEFAULT 0,
            verification_token TEXT,
            pin_expires_at TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            assigned_by INTEGER NOT NULL,
            assigned_to INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            due_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            FOREIGN KEY (assigned_by) REFERENCES users(id),
            FOREIGN KEY (assigned_to) REFERENCES users(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            text TEXT NOT NULL,
            sources TEXT,
            timing REAL,
            hidden BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_archives (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            provider_id INTEGER,
            quarter TEXT NOT NULL,
            year INTEGER NOT NULL,
            message_count INTEGER DEFAULT 0,
            archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (provider_id) REFERENCES users(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS provider_patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(provider_id, user_id),
            FOREIGN KEY (provider_id) REFERENCES users(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS patient_clinical_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            provider_id INTEGER NOT NULL,
            intake_data TEXT DEFAULT '{}',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, provider_id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (provider_id) REFERENCES users(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS therapist_observations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            provider_id INTEGER NOT NULL,
            observations TEXT DEFAULT '{}',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, provider_id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (provider_id) REFERENCES users(id)
        )
    ''')

    conn.commit()
    conn.close()
    print("✅ Database initialized with all tables")


def migrate_db():
    """Add new columns/tables if they don't exist"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    migrations = [
        ("ALTER TABLE users ADD COLUMN pin_expires_at TEXT", "pin_expires_at"),
        ("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'", "role"),
        ("ALTER TABLE chat_messages ADD COLUMN hidden BOOLEAN DEFAULT 0", "hidden"),
    ]

    for sql, name in migrations:
        try:
            cursor.execute(sql)
            print(f"✅ Added {name}")
        except sqlite3.OperationalError:
            pass

    # Create all tables if they don't exist
    tables = [
        '''CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, description TEXT,
            assigned_by INTEGER NOT NULL, assigned_to INTEGER NOT NULL,
            status TEXT DEFAULT 'pending', due_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, completed_at TIMESTAMP,
            FOREIGN KEY (assigned_by) REFERENCES users(id), FOREIGN KEY (assigned_to) REFERENCES users(id))''',
        '''CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
            role TEXT NOT NULL, text TEXT NOT NULL, sources TEXT, timing REAL,
            hidden BOOLEAN DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id))''',
        '''CREATE TABLE IF NOT EXISTS chat_archives (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
            provider_id INTEGER, quarter TEXT NOT NULL, year INTEGER NOT NULL,
            message_count INTEGER DEFAULT 0, archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id), FOREIGN KEY (provider_id) REFERENCES users(id))''',
        '''CREATE TABLE IF NOT EXISTS provider_patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT, provider_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL, assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(provider_id, user_id),
            FOREIGN KEY (provider_id) REFERENCES users(id), FOREIGN KEY (user_id) REFERENCES users(id))''',
        '''CREATE TABLE IF NOT EXISTS patient_clinical_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
            provider_id INTEGER NOT NULL, intake_data TEXT DEFAULT '{}',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(user_id, provider_id),
            FOREIGN KEY (user_id) REFERENCES users(id), FOREIGN KEY (provider_id) REFERENCES users(id))''',
        '''CREATE TABLE IF NOT EXISTS therapist_observations (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
            provider_id INTEGER NOT NULL, observations TEXT DEFAULT '{}',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(user_id, provider_id),
            FOREIGN KEY (user_id) REFERENCES users(id), FOREIGN KEY (provider_id) REFERENCES users(id))''',
    ]

    for sql in tables:
        cursor.execute(sql)

    conn.commit()
    conn.close()
    print("✅ Migration complete")


if __name__ == "__main__":
    init_db()
    migrate_db()


    # 