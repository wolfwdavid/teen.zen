filepath = 'chatbot-rag/backend/api_v2.py'

with open(filepath, 'r') as f:
    lines = f.readlines()

# Find all occurrences of the duplicate blocks
# Keep only the first ensure_verification_table (around line 702) and its call
# Remove the second definition at ~766 and third at ~913

# Strategy: track which blocks to remove
remove_ranges = []

# Find the second 'def ensure_verification_table():' (around 766)
count = 0
for i, line in enumerate(lines):
    if line.strip() == 'def ensure_verification_table():':
        count += 1
        if count == 2:
            # Find end of this function (next line not indented or next def)
            end = i + 1
            while end < len(lines) and (lines[end].startswith('    ') or lines[end].strip() == ''):
                end += 1
            remove_ranges.append((i, end))
            print(f"Marking duplicate #2 for removal: lines {i+1}-{end}")
        elif count == 3:
            # Find end including the call
            end = i + 1
            while end < len(lines) and (lines[end].startswith('    ') or lines[end].strip() == '' or lines[end].strip() == 'ensure_verification_table()'):
                end += 1
            # Also check for UPLOAD_DIR and os.makedirs before it
            start = i
            if start > 0 and 'os.makedirs' in lines[start-1]:
                start -= 1
            if start > 0 and 'UPLOAD_DIR' in lines[start-1]:
                start -= 1
            remove_ranges.append((start, end))
            print(f"Marking duplicate #3 for removal: lines {start+1}-{end}")

# Remove in reverse order to preserve line numbers
new_lines = list(lines)
for start, end in sorted(remove_ranges, reverse=True):
    del new_lines[start:end]
    print(f"Removed lines {start+1}-{end}")

# Also make sure there's an ensure_verification_table() call after the first definition
# Check if it exists
content = ''.join(new_lines)
# Find first def and check if call follows
found_def = False
for i, line in enumerate(new_lines):
    if line.strip() == 'def ensure_verification_table():' and not found_def:
        found_def = True
        # Look for the call within 20 lines
        has_call = False
        for j in range(i+1, min(i+20, len(new_lines))):
            if new_lines[j].strip() == 'ensure_verification_table()':
                has_call = True
                break
            if new_lines[j].strip().startswith('def ') or new_lines[j].strip().startswith('@app'):
                break
        if not has_call:
            # Find end of function
            end = i + 1
            while end < len(new_lines) and (new_lines[end].startswith('    ') or new_lines[end].strip() == ''):
                end += 1
            new_lines.insert(end, '\nensure_verification_table()\n')
            print(f"Added missing ensure_verification_table() call after line {end}")
        break

with open(filepath, 'w') as f:
    f.writelines(new_lines)

print("Done!")
