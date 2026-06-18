from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json
import asyncio

from app.agent import stream_chat, get_chat_history

app = FastAPI()

# Allow CORS for the React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    thread_id: str
    resume: bool = False
    approved: bool = False

@app.get("/chat/history")
async def fetch_history(thread_id: str):
    try:
        history = await get_chat_history(thread_id)
        return {"messages": history}
    except Exception as e:
        return {"error": str(e)}

@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    async def event_generator():
        # Using Server-Sent Events (SSE) format
        try:
            async for chunk_json in stream_chat(request.message, request.thread_id, request.resume, request.approved):
                # We yield the already JSON stringified chunks from agent.py
                yield f"data: {chunk_json}\n\n"
            # Signal the end of the stream
            yield f"data: {json.dumps({'done': True})}\n\n"
        except Exception as e:
            # Handle potential exceptions gracefully
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
