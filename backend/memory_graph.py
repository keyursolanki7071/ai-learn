import sqlite3
import uuid
from typing import Annotated, Literal, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, RemoveMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from app.core.logger import get_logger

load_dotenv()
log = get_logger("memory")

# ==========================================
# 1. State Definition
# ==========================================
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    summary: str

# ==========================================
# 2. Nodes
# ==========================================
llm = ChatOpenAI(model="gpt-4o-mini")

def core_agent_node(state: AgentState):
    summary = state.get("summary", "")
    
    # We provide the summary to the AI as part of its system instructions
    if summary:
        system_message = f"You are a helpful assistant. Here is a summary of the earlier conversation:\n{summary}"
    else:
        system_message = "You are a helpful assistant."
        
    messages = [SystemMessage(content=system_message)] + state["messages"]
    
    response = llm.invoke(messages)
    return {"messages": [response]}


def summarize_conversation(state: AgentState):
    log.info("--- [Memory Manager] Limit reached. Summarizing old messages... ---")
    
    summary = state.get("summary", "")
    messages = state["messages"]
    
    # We want to summarize all messages EXCEPT the last 2 (the most recent Human/AI pair)
    messages_to_summarize = messages[:-2]
    
    if summary:
        prompt = (
            f"This is the current summary: {summary}\n\n"
            "Extend the summary by taking into account the new messages below. "
            "Keep it concise but retain all facts and details about the user.\n\n"
            "New messages to incorporate:"
        )
    else:
        prompt = "Create a concise summary of the conversation below. Retain all facts and details about the user:\n\n"
    
    # Ask the LLM to write the new summary
    summary_message = llm.invoke([
        SystemMessage(content=prompt),
        *messages_to_summarize
    ])
    
    log.info(f"--- [Memory Manager] NEW SUMMARY: {summary_message.content} ---")
    
    # MAGIC STEP: Delete the old messages from the state!
    # LangGraph uses a special object `RemoveMessage` which targets the message's unique ID.
    delete_commands = [RemoveMessage(id=m.id) for m in messages_to_summarize]
    
    return {
        "summary": summary_message.content,
        "messages": delete_commands
    }

# ==========================================
# 3. Conditional Routing
# ==========================================
def should_summarize(state: AgentState) -> Literal["summarize_conversation", END]:
    """Check if the conversation is getting too long."""
    # Let's set a tiny limit of 6 messages so we can see it trigger easily.
    # 6 messages = 3 turns (Human, AI, Human, AI, Human, AI)
    if len(state["messages"]) > 6:
        return "summarize_conversation"
    return END

# ==========================================
# 4. Build the Graph
# ==========================================
graph_builder = StateGraph(AgentState)

graph_builder.add_node("core_agent", core_agent_node)
graph_builder.add_node("summarize_conversation", summarize_conversation)

graph_builder.add_edge(START, "core_agent")
graph_builder.add_conditional_edges("core_agent", should_summarize)
graph_builder.add_edge("summarize_conversation", END)

# We use SqliteSaver to persist the memory across API calls
conn = sqlite3.connect("memory_test.sqlite", check_same_thread=False)
memory = SqliteSaver(conn)

graph = graph_builder.compile(checkpointer=memory)

# ==========================================
# 5. Test Scenarios
# ==========================================
def run_tests():
    # A unique thread ID representing one user's chat session
    config = {"configurable": {"thread_id": "user_123"}}
    
    conversation = [
        "Hi, my name is Keyur.",
        "I am building a really cool AI app using LangGraph.",
        "My favorite programming language is Python.",
        "I have a pet dog named Max.",
        # At this point, there will be 4 human + 4 AI messages = 8 total.
        # This will trigger the Summarizer which deletes older messages!
        "What is my name and what is my dog's name?" 
    ]
    
    for user_input in conversation:
        log.info("\n" + "=" * 50)
        log.info(f"User: {user_input}")
        
        # Invoke the graph
        # Since we use a checkpointer, the state persists between invokes automatically
        result = graph.invoke({"messages": [HumanMessage(content=user_input)]}, config)
        
        log.info(f"AI: {result['messages'][-1].content}")
        log.info("-" * 50)
        log.info(f"Current message count in State: {len(result['messages'])}")
        log.info(f"Current Summary in State: {result.get('summary', 'None')}")
        log.info("=" * 50)

if __name__ == "__main__":
    run_tests()
