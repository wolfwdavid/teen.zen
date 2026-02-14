import sys

filepath = sys.argv[1] if len(sys.argv) > 1 else 'chatbot-rag/backend/api_v2.py'

with open(filepath, 'r') as f:
    content = f.read()

changes = 0

# 1. Reduce chat history from 40 to 10 and truncate more aggressively
old = "cursor.execute('SELECT role, text, created_at FROM chat_messages WHERE user_id = ? ORDER BY created_at DESC LIMIT 40', (patient_id,))"
new = "cursor.execute('SELECT role, text, created_at FROM chat_messages WHERE user_id = ? ORDER BY created_at DESC LIMIT 10', (patient_id,))"
if old in content:
    content = content.replace(old, new, 1)
    changes += 1
    print("[1] Reduced chat history to 10 messages")

# 2. Truncate individual messages more
old = """        chat_lines = [("Patient" if r['role']=='user' else "Bot") + ": " + r['text'][:200] for r in reversed(recent)]"""
new = """        chat_lines = [("Patient" if r['role']=='user' else "Bot") + ": " + r['text'][:80] for r in reversed(recent)]"""
if old in content:
    content = content.replace(old, new, 1)
    changes += 1
    print("[2] Truncated messages to 80 chars")

# 3. Add context truncation before sending to model
old = """        enhanced_question = system_prefix + context + system_suffix + "Therapist question: " + question"""
new = """        # Truncate context to fit model's 2048 token window (~1500 chars for context)
        if len(context) > 1500:
            context = context[:1500] + "..."
        enhanced_question = system_prefix + context + system_suffix + "Therapist question: " + question"""
if old in content:
    content = content.replace(old, new, 1)
    changes += 1
    print("[3] Added context truncation to 1500 chars")

with open(filepath, 'w') as f:
    f.write(content)

print(f"\nDone! {changes} changes applied to {filepath}")
