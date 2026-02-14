filepath = 'chatbot-rag/backend/api_v2.py'

with open(filepath, 'r') as f:
    content = f.read()

# Find the current weather function and replace it
old = "def get_weather_response(location=\"New York\"):"

# Find the entire function
start = content.find(old)
if start == -1:
    print("SKIP - could not find weather function")
    exit()

# Find the next def or top-level statement after this function
end = content.find("\ndef ", start + 10)
if end == -1:
    end = content.find("\n@app", start + 10)
if end == -1:
    end = content.find("\n# ---", start + 10)

old_func = content[start:end]

new_func = '''def get_weather_response(location="New York"):
    try:
        import urllib.request, json as _json, ssl
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        coords = {"New York": (40.71, -74.01), "London": (51.51, -0.13), "Los Angeles": (34.05, -118.24)}
        lat, lon = coords.get(location, (40.71, -74.01))
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m&temperature_unit=fahrenheit&wind_speed_unit=mph"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5, context=ctx) as resp:
            data = _json.loads(resp.read().decode())
        current = data.get("current", {})
        temp = current.get("temperature_2m", "?")
        humidity = current.get("relative_humidity_2m", "?")
        wind = current.get("wind_speed_10m", "?")
        code = current.get("weather_code", 0)
        wmo = {0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
               45: "Foggy", 48: "Rime fog", 51: "Light drizzle", 53: "Moderate drizzle",
               55: "Dense drizzle", 61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
               71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow", 80: "Light showers",
               81: "Moderate showers", 82: "Heavy showers", 95: "Thunderstorm"}
        desc = wmo.get(code, "Unknown")
        return f"Current weather in {location}: {desc}, {temp}\\u00b0F, humidity {humidity}%, wind {wind} mph. Weather can definitely affect mood - sunny days tend to boost energy while grey or rainy days can feel heavy. How are you feeling today?"
    except Exception as e:
        return "I wasn\\'t able to check the current weather right now, but I know weather can affect mood. How are you feeling today?"

'''

content = content[:start] + new_func + content[end:]

with open(filepath, 'w') as f:
    f.write(content)

print("Fixed weather with SSL bypass")
print("Done!")
