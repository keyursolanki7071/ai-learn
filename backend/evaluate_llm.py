from typing import List

from dotenv import load_dotenv
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.core.logger import get_logger

load_dotenv()
log = get_logger("evaluate")

# ==========================================
# 1. Define the Structured Output (The Report Card)
# ==========================================
class EvaluationResult(BaseModel):
    score: int = Field(description="A score from 1 to 5.")
    reasoning: str = Field(description="A concise explanation of why this score was given.")

# ==========================================
# 2. Setup the Judge LLM
# ==========================================
# In production, use the smartest model you can afford for the Judge (e.g., gpt-4o)
# Here we use gpt-4o-mini for speed and cost.
judge_llm = ChatOpenAI(model="gpt-4o-mini").with_structured_output(EvaluationResult)

# ==========================================
# 3. Define the Evaluator Logic
# ==========================================
def evaluate_response(user_query: str, ai_response: str) -> EvaluationResult:
    """Uses an LLM to grade an AI's response based on a specific rubric."""
    
    # The Rubric Prompt
    system_prompt = """
    You are an expert AI Response Evaluator.
    Your job is to grade the AI's response to the User's query based strictly on:
    METRIC: Politeness and Professionalism
    
    RUBRIC:
    1 - Extremely rude, dismissive, or insulting.
    2 - Passive aggressive or annoyed tone.
    3 - Neutral/Robotic. Neither polite nor rude.
    4 - Polite and professional.
    5 - Extremely empathetic, polite, professional, and de-escalates frustration.
    
    You must return a score from 1 to 5, and a short reasoning explaining your grade.
    """
    
    human_prompt = f"USER QUERY:\n{user_query}\n\nAI RESPONSE:\n{ai_response}"
    
    result = judge_llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_prompt)
    ])
    
    return result

# ==========================================
# 4. Test Scenarios (The Dataset)
# ==========================================
def run_evaluation():
    log.info("\n" + "=" * 60)
    log.info("STARTING LLM-AS-A-JUDGE EVALUATION SUITE")
    log.info("=" * 60)
    
    user_query = "Where is my order? Your tracking system is completely broken and I'm tired of waiting!"
    
    # We pretend our AI generated these three different responses to the angry user.
    mock_responses = [
        "It's not broken. You just don't know how to track it. Check your email.",
        "Order 123 is in transit. ETA 2 days.",
        "I am so sorry for the frustration and the trouble with the tracking system! I just checked your order manually, and it is on the way. It should arrive within 2 days."
    ]
    
    total_score = 0
    
    for i, ai_resp in enumerate(mock_responses):
        log.info(f"\n--- TEST CASE {i+1} ---")
        log.info(f"User Query: {user_query}")
        log.info(f"AI Response: {ai_resp}")
        
        log.info("\n[Judge is thinking...]")
        grade: EvaluationResult = evaluate_response(user_query, ai_resp)
        
        log.info(f"SCORE: {grade.score} / 5")
        log.info(f"REASONING: {grade.reasoning}")
        
        total_score += grade.score
        
    avg_score = total_score / len(mock_responses)
    log.info("\n" + "=" * 60)
    log.info(f"EVALUATION COMPLETE. Average Politeness Score: {avg_score:.1f} / 5.0")
    log.info("=" * 60)

if __name__ == "__main__":
    run_evaluation()
