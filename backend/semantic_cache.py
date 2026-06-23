import time
from typing import Optional, Tuple

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from app.core.logger import get_logger

load_dotenv()
log = get_logger("cache")

# ==========================================
# 1. The Math Engine
# ==========================================
def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """
    Calculates the cosine similarity between two vectors.
    Since OpenAI embeddings are pre-normalized, the dot product IS the cosine similarity.
    Returns a score from -1.0 to 1.0 (1.0 means identical).
    """
    return sum(a * b for a, b in zip(v1, v2))


# ==========================================
# 2. The Semantic Cache
# ==========================================
class SemanticCache:
    def __init__(self, threshold: float = 0.95):
        self.threshold = threshold
        # Stores tuples of (embedding_vector, llm_response)
        self.memory: list[Tuple[list[float], str]] = []
        self.embedder = OpenAIEmbeddings(model="text-embedding-3-small")

    def generate_embedding(self, text: str) -> list[float]:
        """Converts text into a mathematical vector."""
        return self.embedder.embed_query(text)

    def check_cache(self, query_embedding: list[float]) -> Tuple[Optional[str], float]:
        """Checks if a similar question has been asked before."""
        best_match_response = None
        highest_similarity = 0.0

        for cached_embedding, cached_response in self.memory:
            sim = cosine_similarity(query_embedding, cached_embedding)
            if sim > highest_similarity:
                highest_similarity = sim
                best_match_response = cached_response

        # If the best match beats our threshold, it's a hit!
        if highest_similarity >= self.threshold:
            return best_match_response, highest_similarity
        
        return None, highest_similarity

    def add_to_cache(self, embedding: list[float], response: str):
        """Saves a new question and its answer to the cache."""
        self.memory.append((embedding, response))


# ==========================================
# 3. The Application Logic
# ==========================================
llm = ChatOpenAI(model="gpt-4o-mini")
cache = SemanticCache(threshold=0.80) # 0.80 is a good threshold for testing

def process_query(user_query: str):
    log.info("\n" + "=" * 60)
    log.info(f"User Query: {user_query}")
    
    start_time = time.time()
    
    # 1. Generate the embedding for the new question (takes ~100ms)
    query_emb = cache.generate_embedding(user_query)
    
    # 2. Check the cache
    cached_response, similarity = cache.check_cache(query_emb)
    
    if cached_response:
        # CACHE HIT! We bypass the LLM completely.
        log.info(f"[CACHE HIT!] Similarity Score: {similarity:.4f}")
        log.info(f"AI Response: {cached_response}")
        source = "Cache"
    else:
        # CACHE MISS! We must ask the real LLM.
        log.info(f"[CACHE MISS] Best similarity was only {similarity:.4f}. Calling LLM...")
        
        response = llm.invoke(user_query).content
        
        # Save to cache for next time
        cache.add_to_cache(query_emb, response)
        log.info(f"AI Response: {response}")
        source = "LLM"
        
    end_time = time.time()
    duration = end_time - start_time
    
    log.info(f"-> Source: {source} | Latency: {duration:.2f} seconds")
    log.info("=" * 60)


# ==========================================
# 4. Test Scenarios
# ==========================================
def run_tests():
    # Query 1: The original question
    process_query("How do I reset my password?")
    
    # Query 2: An unrelated question
    process_query("What is the capital of France?")
    
    # Query 3: Semantically identical to Query 1
    process_query("I forgot my password, how can I reset it?")

if __name__ == "__main__":
    run_tests()
