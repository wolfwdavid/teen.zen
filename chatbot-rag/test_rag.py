import requests
import time

# This script helps you see exactly what your RAG system is retrieving
# to determine if the "bad" responses are due to poor retrieval.

def test_rag_query(query, api_url="http://localhost:8000/query"):
    print(f"--- Testing Query: {query} ---")
    
    payload = {
        "question": query,
        "stream": False
    }

    try:
        # Exponential backoff for reliability
        for delay in [1, 2, 4]:
            response = requests.post(api_url, json=payload)
            if response.status_code == 200:
                data = response.json()
                
                # Check if context is being returned
                context = data.get("context", "NO CONTEXT FOUND")
                answer = data.get("answer", data.get("response", ""))
                
                print(f"Retrieved Context Snippet: {str(context)[:200]}...")
                print(f"Actual Model Answer: {answer}")
                
                if "Hey! You're in my room" in answer:
                    print("\n[!] ALERT: Model is returning a placeholder response.")
                return
            
            time.sleep(delay)
            
    except Exception as e:
        print(f"Error connecting to RAG backend: {e}")

if __name__ == "__main__":
    # Change this to your query and local API endpoint
    test_rag_query("Do my body have any problems that affect our brain function?")