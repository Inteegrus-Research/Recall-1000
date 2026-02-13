from src.database import init_db, get_db
from src.vector_store import VectorStore
from src.memory_engine import MemoryEngine
import os

if __name__ == "__main__":
    if os.path.exists("data/memory.db"):
        os.remove("data/memory.db")
    init_db()
    db = next(get_db())
    vs = VectorStore()
    engine = MemoryEngine(db, vs)

    user = "judge"
    engine.add_memory(user, "food_preference", "Pizza", "preference", 1, 0.95)
    engine.add_memory(user, "food_preference", "Hate Pizza", "preference", 100, 0.95)

    results = engine.retrieve_relevant(user, "What is my food preference?", 101, k=1)
    assert results and "Hate" in results[0]["memory"].value
    print("Core validation passed: retrieved", results[0]["memory"].value)

