from fastapi import FastAPI
from pydantic import BaseModel
from chain import rag_chain

app = FastAPI()

class ChatRequest(BaseModel):
    question: str

@app.post("/chat")
async def chat(req: ChatRequest):
    response = ""
    for chunk in rag_chain.stream(req.question):
        response += chunk
    return {"answer": response}
