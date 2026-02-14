filepath = 'chatbot-rag/backend/api_v2.py'

with open(filepath, 'r') as f:
    lines = f.readlines()

new_lines = []
inserted = False
for i, line in enumerate(lines):
    if not inserted and "# --- HEALTH" in line:
        new_lines.append('\n')
        new_lines.append('# ===== TIME & WEATHER HELPERS =====\n')
        new_lines.append('def detect_time_question(q):\n')
        new_lines.append('    q_lower = q.lower()\n')
        new_lines.append("    time_words = ['what time', 'current time', 'time is it', 'time now', 'what day', 'what date', 'today date', \"today's date\", 'what is today']\n")
        new_lines.append('    return any(w in q_lower for w in time_words)\n')
        new_lines.append('\n')
        new_lines.append('def detect_weather_question(q):\n')
        new_lines.append('    q_lower = q.lower()\n')
        new_lines.append("    weather_words = ['weather', 'temperature', 'forecast', 'raining', 'sunny', 'cloudy', 'snow', 'hot outside', 'cold outside', 'bring umbrella', 'bring a jacket']\n")
        new_lines.append('    return any(w in q_lower for w in weather_words)\n')
        new_lines.append('\n')
        new_lines.append('def get_current_time_response():\n')
        new_lines.append('    from datetime import datetime\n')
        new_lines.append('    now = datetime.now()\n')
        new_lines.append("    return f\"The current date and time is {now.strftime('%A, %B %d, %Y at %I:%M %p')}.\"\n")
        new_lines.append('\n')
        new_lines.append('def get_weather_response(location="New York"):\n')
        new_lines.append('    try:\n')
        new_lines.append('        import urllib.request\n')
        new_lines.append('        url = f"https://wttr.in/{location}?format=%C+%t+%h+%w"\n')
        new_lines.append('        req = urllib.request.Request(url, headers={"User-Agent": "curl/7.68.0"})\n')
        new_lines.append('        with urllib.request.urlopen(req, timeout=5) as resp:\n')
        new_lines.append('            data = resp.read().decode().strip()\n')
        new_lines.append('        return f"Current weather in {location}: {data}. Weather can definitely affect mood - sunny days tend to boost energy while grey or rainy days can feel heavy. How are you feeling today?"\n')
        new_lines.append('    except:\n')
        new_lines.append("        return \"I wasn't able to check the current weather right now, but I know weather can affect mood. How are you feeling today?\"\n")
        new_lines.append('\n')
        inserted = True
        print(f"Inserted helper functions before line {i+1}")
    new_lines.append(line)

with open(filepath, 'w') as f:
    f.writelines(new_lines)

if not inserted:
    print("SKIP - could not find insertion point")
else:
    print("Done!")
