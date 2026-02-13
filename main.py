# main.py
import os
import time
import traceback
from fastapi import FastAPI, BackgroundTasks, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.database import init_db, get_db, get_session
from src.vector_store import VectorStore
from src.memory_engine import MemoryEngine
from src.extractor import extract_memory_candidates
from src.state import load_state_for_user, save_state_for_user
from src.utils import mask_sensitive, estimate_tokens, trunc_to_budget, format_ms
from src.config import TOKEN_BUDGET, RETRIEVE_K
from src.models import MemoryFact

init_db()
VECTOR_STORE = VectorStore()

# rebuild from DB once on startup
session0 = get_session()
try:
    VECTOR_STORE.rebuild_from_db(session0)
finally:
    session0.close()

app = FastAPI(title="Recall-1000 Hackathon API")
USE_LLM = False
GENERATOR = None

class ChatPayload(BaseModel):
    user_id: str = "judge"
    message: str
    turn_id: int

@app.get("/")
def root():
    return {"service": "Recall-1000", "status": "ready"}

@app.get("/debug/memory")
def debug_memory(user_id: str = "judge", db: Session = Depends(get_db)):
    rows = db.query(MemoryFact).filter_by(user_id=user_id, is_active=True).all()
    return {"active_memories": [m.to_dict() for m in rows]}

def process_background_extraction(user_id: str, message: str, turn_id: int):
    try:
        db = get_session()
        engine = MemoryEngine(db, VECTOR_STORE)
        candidates = extract_memory_candidates(message, turn_id)
        for key, value, confidence in candidates:
            existing = db.query(MemoryFact).filter_by(user_id=user_id, key=key, value=value, is_active=True).first()
            if existing:
                existing.last_accessed_turn = turn_id
                db.add(existing)
                continue
            old = db.query(MemoryFact).filter_by(user_id=user_id, key=key, is_active=True).order_by(MemoryFact.last_accessed_turn.desc()).first()
            engine.add_memory(user_id, key, value, turn_id, confidence, category="auto", old_mem=old)
        db.commit()
        db.close()
    except Exception:
        traceback.print_exc()

@app.post("/chat")
def chat(payload: ChatPayload, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    start_total = time.perf_counter()
    engine = MemoryEngine(db, VECTOR_STORE)

    # load + update state
    state = load_state_for_user(db, payload.user_id)
    state.update_from_message(payload.message)

    # immediate extraction: batch add then commit once
    immediate = extract_memory_candidates(payload.message, payload.turn_id)
    new_added = []
    for key, value, confidence in immediate:
        old = db.query(MemoryFact).filter_by(user_id=payload.user_id, key=key, is_active=True).order_by(MemoryFact.last_accessed_turn.desc()).first()
        # use engine.add_memory which commits, but avoid repeated refreshes by letting engine handle it
        mem = engine.add_memory(payload.user_id, key, value, payload.turn_id, confidence, category="extracted", old_mem=old)
        new_added.append(mem)
    # no extra commits here

    # retrieval
    retrieved = engine.retrieve_relevant(user_id=payload.user_id, query=payload.message, turn_id=payload.turn_id, k=RETRIEVE_K, state=state)

    # prepare context with token budget
    context_items = []
    for r in retrieved:
        mem = r["memory"]
        text = f"{mem.key}: {mem.value}"
        context_items.append((text, r["score"]))
    context_items.sort(key=lambda x: x[1], reverse=True)
    truncated = trunc_to_budget(context_items, TOKEN_BUDGET, estimate_tokens)
    context_texts = [t for t, _ in truncated]

    # update access stats (already done in retrieve_relevant) — but ensure persisted
    for r in retrieved:
        db.add(r["memory"])
    db.commit()

    # save conversation state
    save_state_for_user(db, payload.user_id, state, payload.turn_id)

    # response creation (template)
    gen_start = time.perf_counter()
    resp = f"Based on your data: {', '.join(context_texts)}" if context_texts else "Okay. Noted."
    timing_gen = format_ms((time.perf_counter() - gen_start) * 1000.0)

    resp = mask_sensitive(resp)
    adherence = any(v.lower() in resp.lower() for (_k, v, _c) in immediate)

    # background extraction for any remaining facts
    background_tasks.add_task(process_background_extraction, payload.user_id, payload.message, payload.turn_id)

    timing_total = format_ms((time.perf_counter() - start_total) * 1000.0)
    print(f"⏱ Turn {payload.turn_id}: total={timing_total}ms  gen={timing_gen}ms  retrieved={len(retrieved)}")

    return {
        "active_memories": [r["memory"].to_dict() for r in retrieved],
        "response_generated": True,
        "response": resp,
        "timing_ms": {"total": timing_total, "gen": timing_gen},
        "adherence": adherence
    }
