filepath = 'chatbot-rag/backend/api_v2.py'

with open(filepath, 'r') as f:
    content = f.read()

old = """def get_weather_response(location="New York"):
    try:
        import urllib.request
        url = f"https://wttr.in/{location}?format=%C+%t+%h+%w"
        req = urllib.request.Request(url, headers={"User-Agent": "curl/7.68.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = resp.read().decode().strip()
        return f"Current weather in {location}: {data}. Weather can definitely affect mood - sunny days tend to boost energy while grey or rainy days can feel heavy. How are you feeling today?"
    except:
        return "I wasn't able to check the current weather right now, but I know weather can affect mood. How are you feeling today?\""""

new = """def get_weather_response(location="New York"):
    try:
        import subprocess
        result = subprocess.run(
            ['curl', '-s', f'https://wttr.in/{location}?format=%C+%t+%h+%w'],
            capture_output=True, text=True, timeout=8
        )
        data = result.stdout.strip()
        if data and 'Unknown' not in data and len(data) < 200:
            return f"Current weather in {location}: {data}. Weather can definitely affect mood - sunny days tend to boost energy while grey or rainy days can feel heavy. How are you feeling today?"
        else:
            return "I wasn't able to check the current weather right now, but I know weather can affect mood. How are you feeling today?"
    except:
        return "I wasn't able to check the current weather right now, but I know weather can affect mood. How are you feeling today?\""""

if old in content:
    content = content.replace(old, new, 1)
    print("Fixed weather function to use curl subprocess")
else:
    print("SKIP - could not find weather function")

with open(filepath, 'w') as f:
    f.write(content)

print("Done!")
