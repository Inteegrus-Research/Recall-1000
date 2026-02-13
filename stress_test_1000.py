# stress_test_1000.py
import random
import time
import statistics
import math
from src.database import init_db, get_session
from src.vector_store import VectorStore
from src.memory_engine import MemoryEngine
from src.models import MemoryFact

init_db()
db = get_session()
vs = VectorStore()
engine = MemoryEngine(db, vs)

random.seed(42)
USER = "judge"
TOTAL_TURNS = 1000

explicit_queries = 0
implicit_queries = 0

explicit_hits = 0
implicit_presence_hits = 0

precision_counts = []
mrr_list = []
fp_explicit = 0
fp_implicit = 0

retrieval_latencies = []

candidate_keys = [
    "language", "customer_name", "amount_due", "due_date",
    "payment_status", "call_time", "email", "account_info", "preference"
]

def explicit_query(key, turn):
    global explicit_hits, fp_explicit
    q = f"What is my {key}?"
    t0 = time.time()
    retrieved = engine.retrieve_relevant(USER, q, turn, k=3)
    t1 = time.time()
    retrieval_latencies.append((t1 - t0) * 1000.0)
    retrieved_keys = [r["memory"].key for r in retrieved]
    if key in retrieved_keys[:3]:
        explicit_hits += 1
    else:
        fp_explicit += 1
    # Precision@3 computed over returned results (if fewer than 3, normalize)
    topk = retrieved_keys[:3]
    if topk:
        prec = sum(1 for kx in topk if kx == key) / len(topk)
    else:
        prec = 0.0
    precision_counts.append(prec)
    # MRR
    rr = 0.0
    for i, kx in enumerate(topk, start=1):
        if kx == key:
            rr = 1.0 / i
            break
    mrr_list.append(rr)

def implicit_query_call(turn, q_type):
    global implicit_presence_hits, fp_implicit
    if q_type == "call":
        q = "Can you call me tomorrow?"
        expected = "language"
    elif q_type == "remind":
        q = "Remind me about the payment"
        expected = "due_date"
    elif q_type == "schedule":
        q = "What time should I call?"
        expected = "call_time"
    else:
        return
    t0 = time.time()
    retrieved = engine.retrieve_relevant(USER, q, turn, k=5)
    t1 = time.time()
    retrieval_latencies.append((t1 - t0) * 1000.0)
    keys = [r["memory"].key for r in retrieved]
    if expected in keys[:5]:
        implicit_presence_hits += 1
    else:
        fp_implicit += 1

# Seed initial memories
seed = [
    ("language", "Kannada", 0.95, 1),
    ("customer_name", "Johnson", 0.95, 2),
    ("amount_due", "$450", 0.97, 3),
    ("due_date", "February 5", 0.90, 4)
]
for key, value, conf, turn in seed:
    old = db.query(MemoryFact).filter_by(user_id=USER, key=key, is_active=True).first()
    if old:
        old.is_active = False
        db.add(old)
        db.commit()
    engine.add_memory(USER, key, value, turn, conf, category="seed")

for t in range(5, TOTAL_TURNS + 5):
    r = random.random()
    if r < 0.08:
        k = random.choice(candidate_keys)
        if k == "language":
            v = random.choice(["Kannada", "Hindi", "English", "Tamil"])
        elif k == "customer_name":
            v = random.choice(["Alice", "Bob", "Johnson", "Keerthi"])
        elif k == "amount_due":
            v = f"${random.choice([100, 200, 450, 999])}"
        elif k == "due_date":
            v = random.choice(["February 5", "March 10", "April 1"])
        elif k == "payment_status":
            v = random.choice(["pending", "paid", "disputed", "extension_requested"])
        elif k == "call_time":
            v = random.choice(["11AM", "2PM", "after 5PM"])
        else:
            v = f"val_{random.randint(0,999)}"
        old = db.query(MemoryFact).filter_by(user_id=USER, key=k, is_active=True).first()
        engine.add_memory(USER, k, v, t, 0.9, category="random", old_mem=old)
    elif r < 0.16:
        explicit_queries += 1
        k = random.choice(candidate_keys)
        explicit_query(k, t)
    elif r < 0.21:
        implicit_queries += 1
        q_type = random.choice(["call", "remind", "schedule"])
        implicit_query_call(t, q_type)

def percentile(data, p):
    if not data:
        return 0.0
    s = sorted(data)
    idx = int((len(s) - 1) * (p / 100.0))
    return s[idx]

explicit_recall = (explicit_hits / explicit_queries * 100.0) if explicit_queries else 100.0
implicit_presence = (implicit_presence_hits / implicit_queries * 100.0) if implicit_queries else 100.0
prec3 = (sum(precision_counts) / len(precision_counts) * 100.0) if precision_counts else 100.0
mrr = (sum(mrr_list) / len(mrr_list)) if mrr_list else 1.0
total_fp = fp_explicit + fp_implicit
total_queries = max(1, explicit_queries + implicit_queries)
fp_rate = (total_fp / total_queries) * 100.0

lat = retrieval_latencies
avg_lat = statistics.mean(lat) if lat else 0.0
p50 = percentile(lat, 50)
p95 = percentile(lat, 95)
p99 = percentile(lat, 99)

print("=" * 70)
print("RESULTS (1000 turns)")
print("=" * 70)
print(f"Explicit Recall@3:        {explicit_recall:.2f}%")
print(f"Implicit Presence@5:      {implicit_presence:.2f}%")
print(f"Precision@3:              {prec3:.2f}%")
print(f"MRR:                      {mrr:.4f}")
print(f"False Positive@3 Rate:    {fp_rate:.2f}%")
print()
print(f"Avg Latency (ms):         {avg_lat:.2f}")
print(f"P50 Latency:              {p50:.2f}")
print(f"P95 Latency:              {p95:.2f}")
print(f"P99 Latency:              {p99:.2f}")
print("=" * 70)

# Persistence test: reload vector store and check retrieval
print("\nPersistence test: reloading vector store...")
vs2 = VectorStore()
session2 = get_session()
vs2.rebuild_from_db(session2)
sample = vs2.search("language", k=3)
print("Vector search after reload (first few):", sample[:3])
session2.close()
db.close()