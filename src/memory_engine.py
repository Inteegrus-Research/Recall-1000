# src/memory_engine.py
import math
from sqlalchemy.orm import Session
from rapidfuzz import fuzz
from src.models import MemoryFact
from src.config import RETRIEVE_K, ACTIVE_MEMORY_LIMIT, FUZZY_THRESHOLD, RECENCY_HALF_LIFE
from src.utils import recency_weight

# Intent and mapping
INTENT_MAP = {
    "call": ["language", "call_time", "timezone"],
    "remind": ["due_date", "amount_due"],
    "payment": ["amount_due", "payment_status", "due_date"],
    "dispute": ["payment_status", "account_info"]
}

QUERY_TO_KEY_MAP = {
    "language": "language",
    "preferred language": "language",
    "name": "customer_name",
    "customer": "customer_name",
    "amount": "amount_due",
    "amount due": "amount_due",
    "due": "due_date",
    "due date": "due_date",
    "payment": "payment_status",
    "dispute": "payment_status",
    "call": "call_time",
    "account": "account_info",
    "email": "email",
    "preference": "preference"
}

def _query_to_key_candidate(ql: str):
    for phrase, key in QUERY_TO_KEY_MAP.items():
        if phrase in ql:
            return key
    return None

def _words_for_key(key: str):
    return set(key.replace("_", " ").split())

class MemoryEngine:
    def __init__(self, db: Session, vector_store):
        self.db = db
        self.vs = vector_store

    def add_memory(self, user_id: str, key: str, value: str, turn_id: int,
                   confidence: float = 0.9, category: str = "fact", old_mem=None):
        # identical to previous; kept for completeness
        if not old_mem:
            old_mem = self.db.query(MemoryFact).filter(
                MemoryFact.user_id == user_id,
                MemoryFact.key == key,
                MemoryFact.is_active == True
            ).first()

        new = MemoryFact(
            user_id=user_id,
            key=key,
            value=value,
            category=category,
            origin_turn=turn_id,
            last_accessed_turn=turn_id,
            access_count=0,
            confidence=confidence,
            is_active=True
        )
        self.db.add(new)
        self.db.commit()
        self.db.refresh(new)

        if old_mem:
            old_mem.is_active = False
            old_mem.superseded_by = new.id
            new.root_id = old_mem.root_id or old_mem.id
            self.db.add(old_mem)
            self.db.add(new)
            self.db.commit()
        else:
            if not new.root_id:
                new.root_id = new.id
                self.db.add(new)
                self.db.commit()

        try:
            self.vs.add_memory(new.id, f"{new.key}: {new.value}")
        except Exception:
            pass

        self._maybe_evict()
        return new

    def _maybe_evict(self):
        active_count = self.db.query(MemoryFact).filter(MemoryFact.is_active == True).count()
        if active_count <= ACTIVE_MEMORY_LIMIT:
            return
        to_remove = active_count - ACTIVE_MEMORY_LIMIT
        victims = (self.db.query(MemoryFact)
                   .filter(MemoryFact.is_active == True)
                   .order_by(MemoryFact.last_accessed_turn.asc())
                   .limit(to_remove).all())
        for v in victims:
            v.is_active = False
            self.db.add(v)
        self.db.commit()

    def retrieve_relevant(self, user_id: str, query: str, turn_id: int,
                          k: int = RETRIEVE_K, state=None):
        """
        Optimized hybrid retrieval:
         - explicit query pattern and exact key substring (fast)
         - query->key map (dominant)
         - intent map
         - fuzzy over distinct keys (small set)
         - vector fallback: batch fetch MemoryFact rows
        """
        results = []
        ql = query.lower().strip()

        # Tier 0a: explicit-pattern "what is my X" -> attempt canonical mapping
        import re
        m = re.search(r"what(?:'s| is)? my\s+(.+?)[\?\.\!]?$", ql)
        if m:
            target = m.group(1).strip()
            target = re.sub(r'\b(please|now|today)\b', '', target).strip()
            # direct mapping
            cand = None
            for phrase, key in QUERY_TO_KEY_MAP.items():
                if phrase == target or phrase in target or target in phrase:
                    cand = key
                    break
            if not cand:
                candidate_key = target.replace(" ", "_")
                mem = (self.db.query(MemoryFact)
                       .filter(MemoryFact.user_id == user_id,
                               MemoryFact.key == candidate_key,
                               MemoryFact.is_active == True)
                       .order_by(MemoryFact.last_accessed_turn.desc()).first())
                if mem:
                    mem.last_accessed_turn = turn_id
                    mem.access_count = (mem.access_count or 0) + 1
                    self.db.add(mem)
                    self.db.commit()
                    return [{"memory": mem, "score": 100.0}]
            else:
                mem = (self.db.query(MemoryFact)
                       .filter(MemoryFact.user_id == user_id,
                               MemoryFact.key == cand,
                               MemoryFact.is_active == True)
                       .order_by(MemoryFact.last_accessed_turn.desc()).first())
                if mem:
                    mem.last_accessed_turn = turn_id
                    mem.access_count = (mem.access_count or 0) + 1
                    self.db.add(mem)
                    self.db.commit()
                    return [{"memory": mem, "score": 100.0}]

        # Tier 0b: exact key substring using SQL filter (avoids full table scan)
        mem = (self.db.query(MemoryFact)
               .filter(MemoryFact.user_id == user_id,
                       MemoryFact.is_active == True,
                       MemoryFact.key.ilike(f"%{ql}%"))
               .order_by(MemoryFact.last_accessed_turn.desc()).first())
        if mem:
            mem.last_accessed_turn = turn_id
            mem.access_count = (mem.access_count or 0) + 1
            self.db.add(mem)
            self.db.commit()
            return [{"memory": mem, "score": 80.0}]

        # Tier 1: query->key mapping (single lookup)
        q_map_key = _query_to_key_candidate(ql)
        if q_map_key:
            mem = (self.db.query(MemoryFact)
                   .filter(MemoryFact.user_id == user_id,
                           MemoryFact.key == q_map_key,
                           MemoryFact.is_active == True)
                   .order_by(MemoryFact.last_accessed_turn.desc()).first())
            if mem:
                results.append({"memory": mem, "score": 50.0})

        # Tier 2: intent mapping (single queries per intended key)
        for intent, keys in INTENT_MAP.items():
            if intent in ql:
                for key in keys:
                    mem = (self.db.query(MemoryFact)
                           .filter(MemoryFact.user_id == user_id,
                                   MemoryFact.key == key,
                                   MemoryFact.is_active == True)
                           .order_by(MemoryFact.last_accessed_turn.desc()).first())
                    if mem:
                        results.append({"memory": mem, "score": 40.0})

        # Tier 3: fuzzy key match over DISTINCT keys (much smaller set)
        key_rows = (self.db.query(MemoryFact.key)
                    .filter(MemoryFact.user_id == user_id, MemoryFact.is_active == True)
                    .distinct().all())
        key_list = [kr[0] for kr in key_rows]
        fuzzy_candidates = []
        for key in key_list:
            sim = fuzz.partial_ratio(key.lower(), ql) / 100.0
            if sim >= FUZZY_THRESHOLD:
                fuzzy_candidates.append((key, sim))
        # take top few fuzzy keys
        fuzzy_candidates.sort(key=lambda x: x[1], reverse=True)
        for key, sim in fuzzy_candidates[:5]:
            mem = (self.db.query(MemoryFact)
                   .filter(MemoryFact.user_id == user_id,
                           MemoryFact.key == key,
                           MemoryFact.is_active == True)
                   .order_by(MemoryFact.last_accessed_turn.desc()).first())
            if mem:
                results.append({"memory": mem, "score": 30.0 + sim * 5.0})

        # If we already have strong results, dedupe and return
        if any(r["score"] >= 30.0 for r in results):
            best = {}
            for r in results:
                mid = r["memory"].id
                key_words = _words_for_key(r["memory"].key)
                if not any(w in ql for w in key_words):
                    r["score"] *= 0.9
                if mid not in best or r["score"] > best[mid]["score"]:
                    best[mid] = r
            final = list(best.values())
            final.sort(key=lambda x: x["score"], reverse=True)
            # update access stats in batch
            for r in final[:k]:
                m = r["memory"]
                m.last_accessed_turn = turn_id
                m.access_count = (m.access_count or 0) + 1
                self.db.add(m)
            self.db.commit()
            return final[:k]

        # Tier 4: vector fallback (batch fetch MemoryFact rows)
        try:
            vec_hits = self.vs.search(query, k * 5)
            if vec_hits:
                ids = [vid for vid, _ in vec_hits]
                # fetch all mems in one query and build a map
                mem_rows = (self.db.query(MemoryFact)
                            .filter(MemoryFact.id.in_(ids), MemoryFact.user_id == user_id,
                                    MemoryFact.is_active == True).all())
                mem_map = {m.id: m for m in mem_rows}
                for mem_id, sim in vec_hits:
                    mem = mem_map.get(mem_id)
                    if not mem:
                        continue
                    recency = math.exp(-(turn_id - (mem.last_accessed_turn or mem.origin_turn)) / max(1.0, RECENCY_HALF_LIFE/2))
                    score = 0.45 * sim + 0.35 * recency + 0.20 * (mem.confidence or 0.5)
                    results.append({"memory": mem, "score": score})
        except Exception:
            pass

        # Final dedup & penalty for unrelated keys
        best = {}
        for r in results:
            mid = r["memory"].id
            key_words = _words_for_key(r["memory"].key)
            if not any(w in ql for w in key_words):
                r["score"] *= 0.80
            if mid not in best or r["score"] > best[mid]["score"]:
                best[mid] = r

        final = list(best.values())
        final.sort(key=lambda x: x["score"], reverse=True)

        # Update access stats in batch
        for r in final[:k]:
            m = r["memory"]
            m.last_accessed_turn = turn_id
            m.access_count = (m.access_count or 0) + 1
            self.db.add(m)
        self.db.commit()

        return final[:k]
