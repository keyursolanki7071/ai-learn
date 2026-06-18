import os
import json
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END
from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver

from app.tools import send_email

# Load environment variables
load_dotenv()

# Define the state for the graph
class State(TypedDict):
    messages: Annotated[list, add_messages]

# Define the tools array
tools = [send_email]
tool_node = ToolNode(tools)

# Initialize the LLM with streaming enabled
llm = ChatOpenAI(model="gpt-4o-mini", streaming=True)

# Bind the tools to the LLM
llm_with_tools = llm.bind_tools(tools)

# Define the node that calls the LLM
def chatbot(state: State):
    return {"messages": [llm_with_tools.invoke(state["messages"])]}

# Build the LangGraph
graph_builder = StateGraph(State)

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

# Create a MemorySaver for checking state
memory = MemorySaver()

# Compile the graph with a checkpointer and interrupt_before the tools node
agent = graph_builder.compile(
    checkpointer=memory,
    interrupt_before=["tools"]
)

async def stream_chat(message: str, thread_id: str, resume: bool = False, approved: bool = False):
    """
    Stream chat responses and handle breakpoints.
    """
    config = {"configurable": {"thread_id": thread_id}}
    
    if resume:
        if not approved:
            # If the user denies the action, we need to artificially act like the tool failed.
            # We do this by grabbing the pending tool call ID and injecting a ToolMessage.
            state = agent.get_state(config)
            last_message = state.values["messages"][-1]
            tool_calls = getattr(last_message, "tool_calls", [])
            
            if tool_calls:
                from langchain_core.messages import ToolMessage
                tool_msg = ToolMessage(
                    content="Action aborted. The user explicitly denied permission to run this tool.",
                    tool_call_id=tool_calls[0]["id"],
                    name=tool_calls[0]["name"]
                )
                
                # Update the state, pretending the 'tools' node executed this
                agent.update_state(config, {"messages": [tool_msg]}, as_node="tools")
                
            # Now resume graph execution (it will route back to 'chatbot' because of as_node="tools")
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
                
    # After the stream finishes, let's check if the graph is paused/interrupted
    state = agent.get_state(config)
    if state.next and "tools" in state.next:
        # The graph is paused because it wants to call a tool
        # We find the tool call details from the last message
        last_message = state.values["messages"][-1]
        tool_calls = getattr(last_message, "tool_calls", [])
        
        if tool_calls:
            # Tell the client that approval is required
            yield json.dumps({
                "approval_required": True,
                "tool_name": tool_calls[0]["name"],
                "tool_args": tool_calls[0]["args"]
            })
