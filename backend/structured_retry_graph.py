from typing import Annotated, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

# Load environment variables
load_dotenv()


# ==========================================
# 1. Define the Pydantic Schema
# ==========================================
class UserProfile(BaseModel):
    first_name: str = Field(description="The user's first name")
    last_name: str = Field(description="The user's last name")
    age: int = Field(description="The user's age in years")


# ==========================================
# 2. Define the Graph State
# ==========================================
class State(TypedDict):
    messages: Annotated[list, add_messages]
    profile: UserProfile | None
    retry_count: int


# Initialize the LLM
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# Bind the structured output to the LLM
# This forces the LLM to return a JSON object matching UserProfile
structured_llm = llm.with_structured_output(UserProfile)


# ==========================================
# 3. Define the Nodes
# ==========================================
def extract_node(state: State):
    """
    This node asks the LLM to extract the data into our schema.
    """
    print(f"\n--- [Node: Extract] (Attempt {state.get('retry_count', 0) + 1}) ---")

    # We pass the entire conversation history to the LLM.
    # This includes the original text, plus any validation errors from previous loops!
    response = structured_llm.invoke(state["messages"])

    # The response is now a completely structured Python object (UserProfile), not a string!
    return {"profile": response}


def validate_node(state: State):
    """
    This node checks if the extracted profile meets our strict business rules.
    If it fails, we increment the retry count and append an error message.
    """
    print("\n--- [Node: Validate] ---")
    profile = state["profile"]

    # Our Business Rule: The user must be 18 or older.
    if profile.age < 18:
        error_msg = f"Validation Error: You extracted age {profile.age}. The user must be 18 or older. Please carefully read the text and find their true adult age, or infer it if necessary."
        print(f"Validation FAILED: {error_msg}")

        return {
            "retry_count": state.get("retry_count", 0) + 1,
            # We append the error as a message so the LLM sees it on the next loop!
            "messages": [HumanMessage(content=error_msg)],
        }

    print("Validation PASSED!")
    return {"retry_count": state.get("retry_count", 0)}


# ==========================================
# 4. Define the Routing Logic
# ==========================================
def route_after_validation(state: State):
    """
    Decide whether to retry the extraction or finish.
    """
    # If validation passed (meaning the node didn't append an error and increment count,
    # but wait, let's just check the actual age to be safe)
    if state["profile"].age >= 18:
        return END

    # If validation failed, check if we've hit the max retries
    if state.get("retry_count", 0) >= 3:
        print("\n--- [Router] Max retries reached. Giving up. ---")
        return END

    print("\n--- [Router] Looping back to Extract... ---")
    return "extract"


# ==========================================
# 5. Build the Graph
# ==========================================
graph_builder = StateGraph(State)

graph_builder.add_node("extract", extract_node)
graph_builder.add_node("validate", validate_node)

graph_builder.add_edge(START, "extract")
graph_builder.add_edge("extract", "validate")
graph_builder.add_conditional_edges("validate", route_after_validation)

graph = graph_builder.compile()


# ==========================================
# 6. Test the Graph
# ==========================================
def run_test():
    print("=" * 50)
    print("TESTING STRUCTURED OUTPUT & AUTO-RETRY")
    print("=" * 50)

    # Test 1: The messy text contains a trick. The person is 15 but turning 20?
    # Let's see if the LLM falls for it, and if our retry loop catches it.
    messy_text = """
    We have a new user signing up today. His name is Johnathon Doe, but he goes by John.
    When he first tried to sign up for this service, he was only 15 years old, which was back in 2019.
    He is now 20 years old and works as a software engineer.
    """

    # Initial state
    inputs = {
        "messages": [
            SystemMessage(
                content="You are an expert data extractor. Extract the user's profile from the following text."
            ),
            HumanMessage(content=messy_text),
        ],
        "retry_count": 0,
    }

    print("\n[Input Text]:")
    print(messy_text.strip())

    # Run the graph
    result = graph.invoke(inputs)

    print("\n" + "=" * 50)
    print("FINAL RESULT:")
    if result.get("profile"):
        print(f"Name: {result['profile'].first_name} {result['profile'].last_name}")
        print(f"Age: {result['profile'].age}")
    else:
        print("Failed to extract a valid profile.")
    print("=" * 50)


if __name__ == "__main__":
    run_test()
