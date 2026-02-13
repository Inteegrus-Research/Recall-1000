# persistence_test.py
from src.database import init_db, get_session
from src.vector_store import VectorStore
from src.models import MemoryFact

init_db()
db = get_session()
vs = VectorStore()

# Create a sample memory if DB empty
if not db.query(MemoryFact).filter_by(key="language").first():
    mem = MemoryFact(
        user_id="judge",
        key="language",
        value="Kannada",
        origin_turn=1,
        last_accessed_turn=1,
        confidence=0.95,
        is_active=True
    )
    db.add(mem)
    db.commit()
    vs.add_memory(mem.id, f"{mem.key}: {mem.value}")
    print("Saved sample memory.")

print("Simulating restart (reloading vector store)...")
vs2 = VectorStore()
session2 = get_session()
vs2.rebuild_from_db(session2)
res = vs2.search("language", k=3)
print("Search results after reload:", res[:3])
session2.close()
db.close()