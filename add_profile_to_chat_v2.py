filepath = 'chatbot-rag/backend/api_v2.py'

with open(filepath, 'r') as f:
    lines = f.readlines()

# Find line 725 (conn.close()) and 727 (enhanced_question = question)
# Insert profile data loading before conn.close()

new_lines = []
inserted = False
for i, line in enumerate(lines):
    if not inserted and line.strip() == 'conn.close()' and i > 700:
        # Insert profile data loading before conn.close()
        new_lines.append('        # Get user profile data (name, DOB, parents, emergency contact)\n')
        new_lines.append('        try:\n')
        new_lines.append("            cursor.execute('SELECT profile_data FROM user_profile_data WHERE user_id = ?', (patient_id,))\n")
        new_lines.append('            profile_row = cursor.fetchone()\n')
        new_lines.append('            if profile_row:\n')
        new_lines.append('                try:\n')
        new_lines.append("                    pd = json.loads(profile_row['profile_data'])\n")
        new_lines.append('                    profile_parts = []\n')
        new_lines.append("                    if pd.get('fullName'): profile_parts.append('Full name: ' + pd['fullName'])\n")
        new_lines.append("                    if pd.get('preferredName'): profile_parts.append('Goes by: ' + pd['preferredName'])\n")
        new_lines.append("                    if pd.get('pronouns'): profile_parts.append('Pronouns: ' + pd['pronouns'])\n")
        new_lines.append("                    if pd.get('dob'): profile_parts.append('Date of birth: ' + pd['dob'])\n")
        new_lines.append("                    if pd.get('contactPhone'): profile_parts.append('Phone: ' + pd['contactPhone'])\n")
        new_lines.append("                    if pd.get('parent1FullName'): profile_parts.append('Parent/Guardian 1: ' + pd['parent1FullName'] + (' (' + pd.get('parent1EmergencyRelation','') + ')' if pd.get('parent1EmergencyRelation') else ''))\n")
        new_lines.append("                    if pd.get('parent2FullName'): profile_parts.append('Parent/Guardian 2: ' + pd['parent2FullName'] + (' (' + pd.get('parent2EmergencyRelation','') + ')' if pd.get('parent2EmergencyRelation') else ''))\n")
        new_lines.append("                    if pd.get('emergencyName'): profile_parts.append('Emergency contact: ' + pd['emergencyName'])\n")
        new_lines.append('                    if profile_parts:\n')
        new_lines.append("                        context_parts.append('Profile Details: ' + ', '.join(profile_parts))\n")
        new_lines.append('                except: pass\n')
        new_lines.append('        except: pass\n')
        inserted = True
        print(f"Inserted profile data loading before line {i+1}")
    new_lines.append(line)

with open(filepath, 'w') as f:
    f.writelines(new_lines)

print("Done!")
