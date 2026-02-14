import sys

filepath = sys.argv[1] if len(sys.argv) > 1 else 'chatbot-rag/backend/api_v2.py'

with open(filepath, 'r') as f:
    lines = f.readlines()

new_lines = []
i = 0
changes = 0

while i < len(lines):
    line = lines[i]

    # EDIT 1: Replace the context building block
    if '# Build context from patient data if specified' in line:
        # Find the end of this block (conn.close())
        end = i + 1
        while end < len(lines) and 'conn.close()' not in lines[end]:
            end += 1
        end += 1  # include conn.close() line

        # Get indentation
        indent = '    '

        new_lines.append(f'{indent}# Build context from patient data if specified\n')
        new_lines.append(f'{indent}context_parts = []\n')
        new_lines.append(f'{indent}if patient_id:\n')
        new_lines.append(f'{indent}    from auth import get_db_connection\n')
        new_lines.append(f'{indent}    conn = get_db_connection()\n')
        new_lines.append(f'{indent}    cursor = conn.cursor()\n')
        new_lines.append(f'{indent}    # Get patient info - pull ALL available fields\n')
        new_lines.append(f"{indent}    cursor.execute('SELECT username, email, age, phone, role, created_at, last_login FROM users WHERE id = ?', (patient_id,))\n")
        new_lines.append(f'{indent}    patient = cursor.fetchone()\n')
        new_lines.append(f'{indent}    if patient:\n')
        new_lines.append(f"""{indent}        profile_info = [f"Name: {{patient['username']}}"]\n""")
        new_lines.append(f"""{indent}        if patient['age']:\n""")
        new_lines.append(f"""{indent}            profile_info.append(f"Age: {{patient['age']}}")\n""")
        new_lines.append(f"""{indent}        if patient['email']:\n""")
        new_lines.append(f"""{indent}            profile_info.append(f"Email: {{patient['email']}}")\n""")
        new_lines.append(f"""{indent}        if patient['phone']:\n""")
        new_lines.append(f"""{indent}            profile_info.append(f"Phone: {{patient['phone']}}")\n""")
        new_lines.append(f"""{indent}        if patient['created_at']:\n""")
        new_lines.append(f"""{indent}            profile_info.append(f"Joined: {{patient['created_at']}}")\n""")
        new_lines.append(f"""{indent}        if patient['last_login']:\n""")
        new_lines.append(f"""{indent}            profile_info.append(f"Last active: {{patient['last_login']}}")\n""")
        new_lines.append(f"""{indent}        context_parts.append("Patient Profile: " + ", ".join(profile_info))\n""")
        new_lines.append(f'\n')
        new_lines.append(f"{indent}    # Get recent chat messages\n")
        new_lines.append(f"{indent}    cursor.execute('SELECT role, text, created_at FROM chat_messages WHERE user_id = ? ORDER BY created_at DESC LIMIT 40', (patient_id,))\n")
        new_lines.append(f"{indent}    recent = cursor.fetchall()\n")
        new_lines.append(f"{indent}    if recent:\n")
        new_lines.append(f"""{indent}        chat_lines = [("Patient" if r['role']=='user' else "Bot") + ": " + r['text'][:200] for r in reversed(recent)]\n""")
        new_lines.append(f"""{indent}        context_parts.append("Chat History:\\n" + "\\n".join(chat_lines))\n""")
        new_lines.append(f'\n')
        new_lines.append(f"{indent}    # Get clinical intake\n")
        new_lines.append(f"{indent}    try:\n")
        new_lines.append(f"{indent}        cursor.execute('SELECT intake_data FROM clinical_intake WHERE user_id = ? ORDER BY updated_at DESC LIMIT 1', (patient_id,))\n")
        new_lines.append(f"{indent}        intake = cursor.fetchone()\n")
        new_lines.append(f"{indent}        if intake:\n")
        new_lines.append(f"{indent}            try:\n")
        new_lines.append(f"{indent}                intake_data = json.loads(intake['intake_data'])\n")
        new_lines.append(f"{indent}                for key, val in intake_data.items():\n")
        new_lines.append(f"{indent}                    if val:\n")
        new_lines.append(f"""{indent}                        context_parts.append(key.replace('_', ' ').title() + ": " + str(val))\n""")
        new_lines.append(f"{indent}            except: pass\n")
        new_lines.append(f"{indent}    except: pass\n")
        new_lines.append(f'\n')
        new_lines.append(f"{indent}    # Get patient clinical data\n")
        new_lines.append(f"{indent}    try:\n")
        new_lines.append(f"{indent}        cursor.execute('SELECT intake_data FROM patient_clinical_data WHERE user_id = ? ORDER BY updated_at DESC LIMIT 1', (patient_id,))\n")
        new_lines.append(f"{indent}        clinical = cursor.fetchone()\n")
        new_lines.append(f"{indent}        if clinical:\n")
        new_lines.append(f"{indent}            try:\n")
        new_lines.append(f"{indent}                clinical_data = json.loads(clinical['intake_data'])\n")
        new_lines.append(f"{indent}                for key, val in clinical_data.items():\n")
        new_lines.append(f"{indent}                    if val:\n")
        new_lines.append(f"""{indent}                        context_parts.append(key.replace('_', ' ').title() + ": " + str(val))\n""")
        new_lines.append(f"{indent}            except: pass\n")
        new_lines.append(f"{indent}    except: pass\n")
        new_lines.append(f'\n')
        new_lines.append(f"{indent}    # Get assigned tasks\n")
        new_lines.append(f"{indent}    try:\n")
        new_lines.append(f"{indent}        cursor.execute('SELECT title, description, status, due_date FROM tasks WHERE assigned_to = ? ORDER BY created_at DESC LIMIT 10', (patient_id,))\n")
        new_lines.append(f"{indent}        tasks_list = cursor.fetchall()\n")
        new_lines.append(f"{indent}        if tasks_list:\n")
        new_lines.append(f"""{indent}            task_summary = "; ".join([t['title'] + " (status: " + t['status'] + ")" for t in tasks_list])\n""")
        new_lines.append(f"""{indent}            context_parts.append("Assigned Tasks: " + task_summary)\n""")
        new_lines.append(f"{indent}    except: pass\n")
        new_lines.append(f'\n')
        new_lines.append(f"{indent}    # Get knowledge graph topics\n")
        new_lines.append(f"{indent}    graph = extract_knowledge_graph(patient_id)\n")
        new_lines.append(f"{indent}    if graph.get('stats', {{}}).get('top_topics'):\n")
        new_lines.append(f"""{indent}        topics = [t[0] for t in graph['stats']['top_topics'][:5]]\n""")
        new_lines.append(f"""{indent}        context_parts.append("Key topics discussed: " + ", ".join(topics))\n""")
        new_lines.append(f"{indent}    conn.close()\n")

        i = end
        changes += 1
        print("[1] Updated context gathering with full profile, clinical data, tasks")
        continue

    # EDIT 2: Replace the system prompt
    if 'enhanced_question = f"[You are a clinical assistant helping a therapist.' in line:
        indent = '        '
        new_lines.append(indent + 'system_prefix = (\n')
        new_lines.append(indent + '    "[SYSTEM: You are Teen Zen Assistant, a clinical AI helping a licensed therapist. "\n')
        new_lines.append(indent + '    "You have access to the following patient data:\\n\\n"\n')
        new_lines.append(indent + ')\n')
        new_lines.append(indent + 'system_suffix = (\n')
        new_lines.append(indent + '    "\\n\\nINSTRUCTIONS:\\n"\n')
        new_lines.append(indent + '    "- Answer questions about this patient using the data above. If the data contains the answer, provide it directly.\\n"\n')
        new_lines.append(indent + '    "- For profile questions (age, name, etc.), check Patient Profile.\\n"\n')
        new_lines.append(indent + '    "- For behavioral patterns, check Chat History and Key Topics.\\n"\n')
        new_lines.append(indent + '    "- For clinical questions, check Clinical Data and Assigned Tasks.\\n"\n')
        new_lines.append(indent + '    "- If info is NOT in the data, say so and suggest the therapist ask the patient or update intake forms.\\n"\n')
        new_lines.append(indent + '    "- You may also answer general knowledge questions to assist the therapist.\\n"\n')
        new_lines.append(indent + '    "- Be professional, concise, and clinically relevant.]\\n\\n"\n')
        new_lines.append(indent + ')\n')
        new_lines.append(indent + 'enhanced_question = system_prefix + context + system_suffix + "Therapist question: " + question\n')
        i += 1
        changes += 1
        print("[2] Updated system prompt")
        continue

    new_lines.append(line)
    i += 1

with open(filepath, 'w') as f:
    f.writelines(new_lines)

print(f"\nDone! {changes} changes applied to {filepath}")
