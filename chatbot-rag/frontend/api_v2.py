import os
import time
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app) # Enable CORS so your Svelte app can talk to this API

# The API key is provided by the environment at runtime
API_KEY = ""
MODEL_NAME = "gemini-2.5-flash-preview-09-2025"

def generate_rag_response(user_query):
    """
    Calls Gemini 2.5 Flash with Google Search grounding for RAG.
    Implements exponential backoff for reliability.
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={API_KEY}"
    
    payload = {
        "contents": [
            {
                "parts": [{"text": user_query}]
            }
        ],
        "tools": [
            {"google_search": {}}
        ],
        "systemInstruction": {
            "parts": [{"text": "You are a helpful mental health companion. Use the provided search tools to give accurate, empathetic, and evidence-based advice for teenagers."}]
        }
    }

    retries = 5
    for i in range(retries):
        try:
            response = requests.post(url, json=payload)
            if response.status_code == 200:
                result = response.json()
                
                # Extracting text and grounding metadata
                candidate = result.get('candidates', [{}])[0]
                text = candidate.get('content', {}).get('parts', [{}])[0].get('text', "")
                
                sources = []
                grounding = candidate.get('groundingMetadata', {})
                attributions = grounding.get('groundingAttributions', [])
                
                for attr in attributions:
                    if 'web' in attr:
                        sources.append({
                            "title": attr['web'].get('title'),
                            "uri": attr['web'].get('uri')
                        })
                
                return {
                    "text": text,
                    "sources": sources
                }
            
            # If rate limited or server error, back off
            elif response.status_code in [429, 500, 503]:
                time.sleep(2 ** i)
            else:
                return {"error": f"API Error: {response.status_code}"}
        except Exception as e:
            time.sleep(2 ** i)
            if i == retries - 1:
                return {"error": str(e)}

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message')
    
    if not user_message:
        return jsonify({"error": "No message provided"}), 400
    
    response_data = generate_rag_response(user_message)
    return jsonify(response_data)

if __name__ == '__main__':
    app.run(port=5000, debug=True)