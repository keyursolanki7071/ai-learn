from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    thread_id: str
    resume: bool = False
    approved: bool = False
    feedback: str | None = None
