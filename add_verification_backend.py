filepath = 'chatbot-rag/backend/api_v2.py'

with open(filepath, 'r') as f:
    content = f.read()

changes = 0

# 1. Add verification table creation after user_profile_data table
old_table = "CREATE TABLE IF NOT EXISTS user_profile_data"
if "user_verification" not in content:
    # Find the startup/table creation area
    old_startup = "cursor.execute('''CREATE TABLE IF NOT EXISTS user_profile_data"
    # We'll add after the profile data table - find it by looking for the table + close
    # Instead, add endpoints and create table in them
    pass

# 2. Add file upload support
if 'UploadFile' not in content:
    old_import = 'from fastapi import FastAPI, HTTPException, Request, Header, Query'
    new_import = 'from fastapi import FastAPI, HTTPException, Request, Header, Query, UploadFile, File, Form'
    if old_import in content:
        content = content.replace(old_import, new_import, 1)
        changes += 1
        print("[1] Added UploadFile imports")

# 3. Add os import if not present
if 'import os' not in content:
    content = content.replace('import json\n', 'import json\nimport os\n', 1)
    changes += 1
    print("[2] Added os import")

# 4. Add verification endpoints before the health endpoint
old_health = '\n# ===== TIME & WEATHER HELPERS ====='
new_verification = '''
# ===== VERIFICATION SYSTEM =====
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), 'uploads', 'verification')
os.makedirs(UPLOAD_DIR, exist_ok=True)

def ensure_verification_table():
    from auth import get_db_connection
    conn = get_db_connection()
    conn.execute(\'\'\'CREATE TABLE IF NOT EXISTS user_verification (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    )\'\'\')
    conn.commit()
    conn.close()

ensure_verification_table()

@app.post('/api/verification/upload')
async def upload_verification(
    id_document: UploadFile = File(None),
    video: UploadFile = File(None),
    authorization: str = Header(None)
):
    user = get_current_user(authorization)
    from auth import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create user directory
    user_dir = os.path.join(UPLOAD_DIR, str(user['id']))
    os.makedirs(user_dir, exist_ok=True)

    id_path = None
    video_path = None

    if id_document:
        ext = os.path.splitext(id_document.filename)[1] or '.jpg'
        id_path = os.path.join(user_dir, f'id_document{ext}')
        with open(id_path, 'wb') as f:
            f.write(await id_document.read())

    if video:
        ext = os.path.splitext(video.filename)[1] or '.webm'
        video_path = os.path.join(user_dir, f'verification_video{ext}')
        with open(video_path, 'wb') as f:
            f.write(await video.read())

    # Check if existing record
    cursor.execute('SELECT id FROM user_verification WHERE user_id = ?', (user['id'],))
    existing = cursor.fetchone()

    if existing:
        updates = ["status = 'pending'", "updated_at = CURRENT_TIMESTAMP"]
        params = []
        if id_path:
            updates.append("id_document_path = ?")
            params.append(id_path)
        if video_path:
            updates.append("video_path = ?")
            params.append(video_path)
        params.append(user['id'])
        cursor.execute(f"UPDATE user_verification SET {', '.join(updates)} WHERE user_id = ?", params)
    else:
        cursor.execute(
            "INSERT INTO user_verification (user_id, id_document_path, video_path) VALUES (?, ?, ?)",
            (user['id'], id_path, video_path)
        )

    conn.commit()
    conn.close()
    return {"status": "uploaded", "message": "Verification documents submitted for review"}

@app.get('/api/verification/status')
async def get_verification_status(authorization: str = Header(None)):
    user = get_current_user(authorization)
    from auth import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT status, created_at, updated_at, rejection_reason FROM user_verification WHERE user_id = ?', (user['id'],))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return {"status": "not_submitted"}
    return {"status": row['status'], "created_at": row['created_at'], "updated_at": row['updated_at'], "rejection_reason": row['rejection_reason']}

@app.get('/api/provider/patients/{user_id}/verification')
async def get_patient_verification(user_id: int, authorization: str = Header(None)):
    user = get_current_user(authorization)
    require_provider(user)
    from auth import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM user_verification WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return {"status": "not_submitted"}
    return {
        "status": row['status'],
        "id_document_path": row['id_document_path'],
        "video_path": row['video_path'],
        "created_at": row['created_at'],
        "reviewed_by": row['reviewed_by'],
        "reviewed_at": row['reviewed_at'],
        "rejection_reason": row['rejection_reason']
    }

@app.post('/api/provider/patients/{user_id}/verification/review')
async def review_verification(user_id: int, request: Request, authorization: str = Header(None)):
    user = get_current_user(authorization)
    require_provider(user)
    body = await request.json()
    action = body.get('action')  # 'approve' or 'reject'
    reason = body.get('reason', '')
    from auth import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()
    if action == 'approve':
        cursor.execute("UPDATE user_verification SET status = 'approved', reviewed_by = ?, reviewed_at = CURRENT_TIMESTAMP WHERE user_id = ?", (user['id'], user_id))
    elif action == 'reject':
        cursor.execute("UPDATE user_verification SET status = 'rejected', reviewed_by = ?, reviewed_at = CURRENT_TIMESTAMP, rejection_reason = ? WHERE user_id = ?", (user['id'], user_id, reason))
    conn.commit()
    conn.close()
    return {"status": action + "d"}

@app.get('/api/verification/file/{user_id}/{filename}')
async def serve_verification_file(user_id: int, filename: str, authorization: str = Header(None)):
    user = get_current_user(authorization)
    # Only the user themselves or a provider can view
    if user['role'] != 'provider' and user['id'] != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    from fastapi.responses import FileResponse
    file_path = os.path.join(UPLOAD_DIR, str(user_id), filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)

# 5. Add campus/orphanage to provider chat context
'''

if old_health in content:
    content = content.replace(old_health, new_verification + '\n# ===== TIME & WEATHER HELPERS =====', 1)
    changes += 1
    print("[3] Added verification endpoints")

# 6. Add campus/orphanage to the profile context in provider chat
old_emergency = "                    if pd.get('emergencyName'): profile_parts.append('Emergency contact: ' + pd['emergencyName'])"
new_emergency = """                    if pd.get('emergencyName'): profile_parts.append('Emergency contact: ' + pd['emergencyName'])
                    if pd.get('campusName'): profile_parts.append('Campus/School: ' + pd['campusName'])
                    if pd.get('orphanageName'): profile_parts.append('Orphanage/Home: ' + pd['orphanageName'])"""

if old_emergency in content:
    content = content.replace(old_emergency, new_emergency, 1)
    changes += 1
    print("[4] Added campus/orphanage to provider chat context")

with open(filepath, 'w') as f:
    f.write(content)

print(f"\nDone! {changes} changes applied")
