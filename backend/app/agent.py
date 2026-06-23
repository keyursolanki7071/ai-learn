import json
from collections.abc import AsyncGenerator
from typing import Annotated
from typing_extensions import TypedDict

from langchain_core.messages import ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from app.core.config import settings
from app.tools import send_email

# Define the state for the graph
class State(TypedDict):
    messages: Annotated[list, add_messages]

# Define the tools array
tools = [send_email]
tool_node = ToolNode(tools)

# Initialize the LLM with streaming enabled
llm = ChatOpenAI(
    model="gpt-4o-mini", 
    streaming=True, 
    api_key=settings.OPENAI_API_KEY
)

# Bind the tools to the LLM
llm_with_tools = llm.bind_tools(tools)

# Define the node that calls the LLM
def chatbot(state: State):
    return {"messages": [llm_with_tools.invoke(state["messages"])]}

# Build the LangGraph
graph_builder = StateGraph(State) # type: ignore

# Add nodes
graph_builder.add_node("chatbot", chatbot)
graph_builder.add_node("tools", tool_node)

# Add edges
graph_builder.add_edge(START, "chatbot")

# Add conditional edge to check if a tool was called
graph_builder.add_conditional_edges(
    "chatbot",
    tools_condition,
)

# Return back to the chatbot after running tools
graph_builder.add_edge("tools", "chatbot")

async def get_chat_history(thread_id: str, checkpointer: AsyncSqliteSaver) -> list[dict]:
    """Fetch formatted chat history from the checkpointer for the given thread_id."""
    agent = graph_builder.compile(checkpointer=checkpointer, interrupt_before=["tools"])
    config = {"configurable": {"thread_id": thread_id}}
    state = await agent.aget_state(config)
    
    if not state or not state.values or "messages" not in state.values:
        return []
        
    history = []
    for msg in state.values["messages"]:
        # We only want to send Human and AI messages to the frontend to populate UI
        role = "user" if msg.type == "human" else "ai"
        
        # If it's a tool message or an AI message with a tool call, we can skip or format it
        if msg.type == "tool":
            continue
            
        content = msg.content
        if isinstance(content, list):
            # Sometimes content is a list of blocks
            content = " ".join([block.get("text", "") for block in content if isinstance(block, dict)])
            
        # If it has tool calls, we might want to skip showing the blank AI message 
        if msg.type == "ai" and not content and getattr(msg, "tool_calls", []):
            continue
            
        history.append({
            "id": getattr(msg, "id", None) or str(hash(content)),
            "role": role,
            "content": content,
            "timestamp": None 
        })
        
    return history

async def stream_chat(
    message: str, 
    thread_id: str, 
    checkpointer: AsyncSqliteSaver,
    resume: bool = False, 
    approved: bool = False, 
    feedback: str | None = None
) -> AsyncGenerator[str, None]:
    """
    Stream chat responses and handle breakpoints.
    """
    agent = graph_builder.compile(checkpointer=checkpointer, interrupt_before=["tools"])
    config = {"configurable": {"thread_id": thread_id}}
    
    if resume:
        if not approved:
            # If the user denies the action, we artificially act like the tool failed.
            state = await agent.aget_state(config)
            last_message = state.values["messages"][-1]
            tool_calls = getattr(last_message, "tool_calls", [])
            
            if tool_calls:
                denial_msg = "Action aborted. User explicitly denied permission."
                if feedback:
                    denial_msg = f"Action aborted. User rejected the draft and requested the following changes: {feedback}"
                    
                tool_msg = ToolMessage(
                    content=denial_msg,
                    tool_call_id=tool_calls[0]["id"],
                    name=tool_calls[0]["name"]
                )
                
                # Update the state, pretending the 'tools' node executed this
                await agent.aupdate_state(config, {"messages": [tool_msg]}, as_node="tools")
                
            inputs = None
        else:
            # Resume exactly where we left off (at the tools node)
            inputs = None
    else:
        # Initial message
        inputs = {"messages": [("user", message)]}
    
    # We use astream_events to get granular streaming of the LLM tokens
    async for event in agent.astream_events(inputs, config, version="v1"):
        kind = event["event"]
        if kind == "on_chat_model_stream":
            content = event["data"]["chunk"].content
            if content and isinstance(content, str):
                yield json.dumps({"chunk": content})
                
    # After the stream finishes, check if the graph is paused/interrupted
    state = await agent.aget_state(config)
    if state.next and "tools" in state.next:
        last_message = state.values["messages"][-1]
        tool_calls = getattr(last_message, "tool_calls", [])
        
        if tool_calls:
            yield json.dumps({
                "approval_required": True,
                "tool_name": tool_calls[0]["name"],
                "tool_args": tool_calls[0]["args"]
            })
