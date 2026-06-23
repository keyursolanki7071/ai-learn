import operator
from typing import Annotated, Any, Literal, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, BaseMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

from app.core.logger import get_logger

load_dotenv()

log = get_logger("multi_agent")

# ==========================================
# 1. Define the State
# ==========================================
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    next: str
    instruction: str


# ==========================================
# 2. Define Supervisor Output Schema
# ==========================================
# The Supervisor will output this structured data to route the graph.
members = ["Researcher", "Writer"]
options = ["FINISH"] + members

class route(BaseModel):
    next: Literal["FINISH", "Researcher", "Writer"] = Field(
        description="The next agent to route to, or FINISH if the task is complete."
    )
    instruction: str = Field(
        default="",
        description="The specific, narrow sub-task the chosen worker must execute right now."
    )

llm = ChatOpenAI(model="gpt-4o-mini")

# ==========================================
# 3. Define the Supervisor Node
# ==========================================
supervisor_prompt = (
    "You are a supervisor tasked with managing a conversation between the "
    f"following workers: {members}. Given the following user request, "
    "respond with the worker to act next. Each worker will perform a "
    "task and respond with their results and status. When finished, "
    "respond with FINISH."
)

def supervisor_node(state: AgentState):
    log.info("--- [Supervisor] Thinking... ---")
    messages = [SystemMessage(content=supervisor_prompt)] + state["messages"]
    
    # We use structured output to force it to return a valid next route
    supervisor_llm = llm.with_structured_output(route)
    response = supervisor_llm.invoke(messages)
    
    # response is a `route` Pydantic object
    log.info(f"--- [Supervisor] Routing to: {response.next} | Instruction: {response.instruction} ---")
    return {"next": response.next, "instruction": response.instruction}


# ==========================================
# 4. Define Sub-Agent Nodes
# ==========================================
# A helper function to create worker nodes
def create_agent_node(agent_name: str, system_prompt: str):
    def agent_node(state: AgentState):
        log.info(f"--- [Agent: {agent_name}] Working... ---")
        # Give the agent its core identity, plus the exact instruction from the supervisor
        instruction_prompt = f"{system_prompt}\n\nYOUR CURRENT SUB-TASK FROM THE SUPERVISOR:\n{state.get('instruction', '')}"
        messages = [SystemMessage(content=instruction_prompt)] + state["messages"]
        response = llm.invoke(messages)
        
        # We wrap the result in a HumanMessage with the agent's name
        # so the Supervisor knows who said this in the history.
        return {
            "messages": [
                HumanMessage(content=response.content, name=agent_name)
            ]
        }
    return agent_node

researcher_node = create_agent_node(
    "Researcher", 
    "You are an expert researcher. Since you do not have internet access right now, "
    "use your internal knowledge to gather comprehensive and accurate facts about the topic. "
    "Provide detailed notes for the writer."
)

writer_node = create_agent_node(
    "Writer",
    "You are an expert technical writer. Synthesize the notes provided by the researcher "
    "into a concise, well-written summary. Format your output clearly."
)


# ==========================================
# 5. Build the Graph
# ==========================================
graph_builder = StateGraph(AgentState)

# Add nodes
graph_builder.add_node("supervisor", supervisor_node)
graph_builder.add_node("Researcher", researcher_node)
graph_builder.add_node("Writer", writer_node)

# Add edges
graph_builder.add_edge(START, "supervisor")

# The supervisor routes to either a worker or FINISH
# We use conditional edges to check the "next" state variable
graph_builder.add_conditional_edges(
    "supervisor",
    lambda x: x["next"],
    {
        "Researcher": "Researcher",
        "Writer": "Writer",
        "FINISH": END
    }
)

# Workers always route back to the supervisor
graph_builder.add_edge("Researcher", "supervisor")
graph_builder.add_edge("Writer", "supervisor")

graph = graph_builder.compile()


# ==========================================
# 6. Test the Graph
# ==========================================
def run_test():
    log.info("=" * 50)
    log.info("TESTING MULTI-AGENT SUPERVISOR WORKFLOW")
    log.info("=" * 50)

    # Initial state
    inputs = {
        "messages": [
            HumanMessage(
                content="Task: Write a 2-paragraph essay about the Apollo 11 mission. "
                        "Workflow: The Supervisor MUST route to the Researcher to get facts. Then route to the Writer to draft the essay. "
                        "Then the Supervisor MUST route to the Researcher AGAIN to verify the essay for missing details. "
                        "Then the Supervisor MUST route to the Writer AGAIN to write the final revised essay."
            )
        ],
        "instruction": ""
    }

    # Run the graph
    # We use stream so we can see the output of each node as it happens
    for chunk in graph.stream(inputs, stream_mode="updates"):
        # chunk is a dict where the key is the node name that just ran
        for node_name, state_update in chunk.items():
            if node_name != "supervisor":
                # Print what the worker produced
                last_message = state_update["messages"][-1]
                log.info(f"[{node_name} Output]:\n{last_message.content[:200]}...")

    log.info("=" * 50)
    log.info("WORKFLOW COMPLETE")
    log.info("=" * 50)

if __name__ == "__main__":
    run_test()
