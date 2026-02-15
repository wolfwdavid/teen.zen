filepath = 'chatbot-rag/backend/api_v2.py'

with open(filepath, 'r') as f:
    content = f.read()

# Find where profile_parts are built and add accurate age calc from DOB
old = "                    if pd.get('fullName'): profile_parts.append('Full name: ' + pd['fullName'])"

new = """                    if pd.get('dob'):
                        try:
                            from datetime import datetime
                            dob = datetime.strptime(pd['dob'], '%Y-%m-%d')
                            today = datetime.now()
                            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
                            profile_parts.append('Age: ' + str(age) + ' years old (DOB: ' + pd['dob'] + ')')
                        except: pass
                    if pd.get('fullName'): profile_parts.append('Full name: ' + pd['fullName'])"""

if old in content:
    content = content.replace(old, new, 1)
    print("Added accurate age calculation from DOB")
else:
    print("SKIP - could not find insertion point")

with open(filepath, 'w') as f:
    f.write(content)

print("Done!")
