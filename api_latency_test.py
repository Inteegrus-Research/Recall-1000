# api_latency_test.py
import requests
import time
import statistics
import os

URL = os.getenv("API_URL", "http://127.0.0.1:8000/chat")
payload = {"user_id": "judge", "message": "What is my language?", "turn_id": 1000}
times = []
for i in range(100):
    t0 = time.time()
    try:
        requests.post(URL, json=payload, timeout=10)
        times.append((time.time() - t0) * 1000.0)
    except Exception:
        times.append(10000.0)

def pct(arr, p):
    s = sorted(arr)
    return s[int(len(s) * p / 100)]

print("=" * 60)
print("END-TO-END API LATENCY RESULTS")
print("=" * 60)
print(f"Requests: {len(times)}")
print(f"Avg Latency (ms): {round(statistics.mean(times), 2)}")
print(f"P50 Latency (ms): {round(pct(times, 50), 2)}")
print(f"P95 Latency (ms): {round(pct(times, 95), 2)}")
print(f"P99 Latency (ms): {round(pct(times, 99), 2)}")
print("=" * 60)