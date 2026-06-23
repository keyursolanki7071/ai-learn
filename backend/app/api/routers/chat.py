import json

from fastapi import APIRouter, Depends, HTTPException, Request
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from sse_starlette.sse import EventSourceResponse

from app.agent import get_chat_history, stream_chat
from app.schemas.chat import ChatRequest

router = APIRouter()


def get_checkpointer(request: Request) -> AsyncSqliteSaver:
    return request.app.state.checkpointer


@router.get("/history")
async def fetch_history(thread_id: str, checkpointer: AsyncSqliteSaver = Depends(get_checkpointer)):
    try:
        history = await get_chat_history(thread_id, checkpointer)
        return {"messages": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/stream")
async def chat_stream_endpoint(
    request: ChatRequest, checkpointer: AsyncSqliteSaver = Depends(get_checkpointer)
):
    async def event_generator():
        try:
            async for chunk_json in stream_chat(
                message=request.message,
                thread_id=request.thread_id,
                checkpointer=checkpointer,
                resume=request.resume,
                approved=request.approved,
                feedback=request.feedback,
            ):
                yield {"data": chunk_json}
            yield {"data": json.dumps({"done": True})}
        except Exception as e:
            yield {"data": json.dumps({"error": str(e)})}

    return EventSourceResponse(event_generator())
