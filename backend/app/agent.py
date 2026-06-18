import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END
from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages

# Load environment variables
load_dotenv()

# Define the state for the graph
class State(TypedDict):
    messages: Annotated[list, add_messages]

# Initialize the LLM with streaming enabled
llm = ChatOpenAI(model="gpt-4o-mini", streaming=True)

# Define the node that calls the LLM
def chatbot(state: State):
    return {"messages": [llm.invoke(state["messages"])]}

# Build the LangGraph
graph_builder = StateGraph(State)
graph_builder.add_node("chatbot", chatbot)
graph_builder.add_edge(START, "chatbot")
graph_builder.add_edge("chatbot", END)

# Compile the graph
agent = graph_builder.compile()

async def stream_chat(message: str):
    """
    Stream chat responses using LangGraph's astream_events.
    """
    inputs = {"messages": [("user", message)]}
    
    # We use astream_events to get granular streaming of the LLM tokens
    async for event in agent.astream_events(inputs, version="v1"):
        kind = event["event"]
        if kind == "on_chat_model_stream":
            content = event["data"]["chunk"].content
            if content:
                yield content
