from db import get_db_connection


def migrate_db():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT DEFAULT 'user',
        age INTEGER,
        phone TEXT,
        email_verified INTEGER DEFAULT 0,
        verification_token TEXT,
        pin_expires_at TEXT,
        profile_pic TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login TIMESTAMP
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS tasks (
        id SERIAL PRIMARY KEY,
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
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS chat_messages (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL,
        role TEXT NOT NULL,
        text TEXT NOT NULL,
        sources TEXT,
        timing REAL,
        hidden INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS chat_archives (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL,
        provider_id INTEGER,
        quarter TEXT NOT NULL,
        year INTEGER NOT NULL,
        message_count INTEGER DEFAULT 0,
        archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (provider_id) REFERENCES users(id)
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS provider_patients (
        id SERIAL PRIMARY KEY,
        provider_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(provider_id, user_id),
        FOREIGN KEY (provider_id) REFERENCES users(id),
        FOREIGN KEY (user_id) REFERENCES users(id)
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS patient_clinical_data (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL,
        provider_id INTEGER NOT NULL,
        intake_data TEXT DEFAULT '{}',
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, provider_id),
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (provider_id) REFERENCES users(id)
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS therapist_observations (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL,
        provider_id INTEGER NOT NULL,
        observations TEXT DEFAULT '{}',
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, provider_id),
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (provider_id) REFERENCES users(id)
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS user_verification (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL,
        id_document_path TEXT,
        video_path TEXT,
        status TEXT DEFAULT 'pending',
        reviewed_by INTEGER,
        reviewed_at TIMESTAMP,
        rejection_reason TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS email_verification (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL,
        email TEXT NOT NULL,
        code TEXT NOT NULL,
        expires_at TIMESTAMP NOT NULL,
        verified INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )""")

    for sql in [
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS pin_expires_at TEXT",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS role TEXT DEFAULT 'user'",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS profile_pic TEXT",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified INTEGER DEFAULT 0",
        "ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS hidden INTEGER DEFAULT 0",
    ]:
        cur.execute(sql)

    conn.commit()
    cur.close()
    conn.close()
    print("Migration complete")


if __name__ == "__main__":
    migrate_db()
