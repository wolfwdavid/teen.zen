filepath = 'chatbot-rag/backend/api_v2.py'

with open(filepath, 'r') as f:
    content = f.read()

changes = 0

# 1. Add imports and helper functions after existing imports
# Find the last import line area
old_import = "from fastapi.responses import StreamingResponse"
new_import = """from fastapi.responses import StreamingResponse
import urllib.request
from datetime import datetime, timezone"""

if 'urllib.request' not in content:
    content = content.replace(old_import, new_import, 1)
    changes += 1
    print("[1] Added urllib and datetime imports")

# 2. Add helper functions before the first route
old_route = '@app.get("/health")'
helper_funcs = '''
# ===== TIME & WEATHER HELPERS =====
def detect_time_question(q):
    q_lower = q.lower()
    time_words = ['what time', 'current time', 'time is it', 'time now', 'what day', 'what date', 'today date', "today's date", 'what is today']
    return any(w in q_lower for w in time_words)

def detect_weather_question(q):
    q_lower = q.lower()
    weather_words = ['weather', 'temperature', 'forecast', 'raining', 'sunny', 'cloudy', 'snow', 'hot outside', 'cold outside', 'bring umbrella', 'bring a jacket']
    return any(w in q_lower for w in weather_words)

def get_current_time_response():
    now = datetime.now()
    return f"The current date and time is {now.strftime('%A, %B %d, %Y at %I:%M %p')}."

def get_weather_response(location="New York"):
    try:
        url = f"https://wttr.in/{location}?format=%C+%t+%h+%w"
        req = urllib.request.Request(url, headers={"User-Agent": "curl/7.68.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = resp.read().decode().strip()
        return f"Current weather in {location}: {data}. Weather can definitely affect mood - sunny days tend to boost energy while grey or rainy days can feel heavy. How are you feeling today?"
    except:
        return f"I wasn't able to check the current weather right now, but I know weather can affect mood. How are you feeling today?"

''' + '@app.get("/health")'

if 'detect_time_question' not in content:
    content = content.replace(old_route, helper_funcs, 1)
    changes += 1
    print("[2] Added time/weather helper functions")

# 3. Add time/weather interception to the USER chat stream
old_user_stream = """    async def event_generator():
        try:
            logger.info(f"🔍 [Stream] Question: {question}")
            if chain_v2.rag_chain is None:
                yield f"data: {json.dumps({'type': 'error', 'message': 'RAG system not initialized'})}\\n\\n"
                return
            full_text = ""
            for token in chain_v2.rag_chain.stream(question):"""

new_user_stream = """    async def event_generator():
        try:
            logger.info(f"🔍 [Stream] Question: {question}")
            if chain_v2.rag_chain is None:
                yield f"data: {json.dumps({'type': 'error', 'message': 'RAG system not initialized'})}\\n\\n"
                return

            # Intercept time/weather questions
            if detect_time_question(question):
                answer = get_current_time_response()
                yield f"data: {json.dumps({'type': 'token', 'text': answer})}\\n\\n"
                yield f"data: {json.dumps({'type': 'done'})}\\n\\n"
                return
            if detect_weather_question(question):
                answer = get_weather_response()
                yield f"data: {json.dumps({'type': 'token', 'text': answer})}\\n\\n"
                yield f"data: {json.dumps({'type': 'done'})}\\n\\n"
                return

            full_text = ""
            for token in chain_v2.rag_chain.stream(question):"""

if old_user_stream in content:
    content = content.replace(old_user_stream, new_user_stream, 1)
    changes += 1
    print("[3] Added time/weather interception to user chat stream")

# 4. Add time/weather interception to the PROVIDER chat stream
old_provider_stream = """            logger.info(f"🔍 [Provider Stream] Q: {question} | Patient: {patient_id}")
            if chain_v2.rag_chain is None:
                yield f"data: {json.dumps({'type': 'error', 'message': 'RAG system not initialized'})}\\n\\n"
                return
            for token in chain_v2.rag_chain.stream(enhanced_question):"""

new_provider_stream = """            logger.info(f"🔍 [Provider Stream] Q: {question} | Patient: {patient_id}")
            if chain_v2.rag_chain is None:
                yield f"data: {json.dumps({'type': 'error', 'message': 'RAG system not initialized'})}\\n\\n"
                return

            # Intercept time/weather questions for provider too
            if detect_time_question(question):
                answer = get_current_time_response()
                yield f"data: {json.dumps({'type': 'token', 'text': answer})}\\n\\n"
                yield f"data: {json.dumps({'type': 'done'})}\\n\\n"
                return
            if detect_weather_question(question):
                answer = get_weather_response()
                yield f"data: {json.dumps({'type': 'token', 'text': answer})}\\n\\n"
                yield f"data: {json.dumps({'type': 'done'})}\\n\\n"
                return

            for token in chain_v2.rag_chain.stream(enhanced_question):"""

if old_provider_stream in content:
    content = content.replace(old_provider_stream, new_provider_stream, 1)
    changes += 1
    print("[4] Added time/weather interception to provider chat stream")

with open(filepath, 'w') as f:
    f.write(content)

print(f"\nDone! {changes} changes applied")
