# latency_breakdown.py
import time
import statistics
from src.extractor import extract_memory_candidates
from src.vector_store import VectorStore
from src.database import init_db

init_db()
vs = VectorStore()

texts = [
    "My preferred language is Kannada",
    "Call me after 11 AM tomorrow",
    "I already paid the $450 yesterday",
    "Please extend due date to March 10",
    "My name is Johnson and account ending in 4582"
] * 10

def measure(func, n=50):
    times = []
    for _ in range(n):
        t0 = time.time()
        func()
        times.append((time.time() - t0) * 1000.0)
    return times

# Extraction latency
ext_times = measure(lambda: [extract_memory_candidates(t, 1) for t in texts], n=20)
# Search latency (includes vectorization)
search_times = measure(lambda: [vs.search(t, k=5) for t in texts], n=20)

def stats(arr):
    s = sorted(arr)
    n = len(s)
    return {
        "mean": round(statistics.mean(s), 3),
        "p50": round(s[int(n * 0.5)], 3),
        "p95": round(s[int(max(0, n * 0.95 - 1))], 3)
    }

print("Extraction (ms):", stats(ext_times))
print("Search (ms):", stats(search_times))