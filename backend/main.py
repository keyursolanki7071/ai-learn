from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json
import asyncio

from app.agent import stream_chat

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

@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    async def event_generator():
        # Using Server-Sent Events (SSE) format
        try:
            async for chunk in stream_chat(request.message):
                # Send each chunk as an SSE data payload
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
            # Signal the end of the stream
            yield f"data: {json.dumps({'done': True})}\n\n"
        except Exception as e:
            # Handle potential exceptions gracefully
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
