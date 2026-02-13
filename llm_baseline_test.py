# llm_baseline_test.py
# Uncomment if LLM dependencies installed

import time
import statistics
from transformers import pipeline
import torch

torch.set_num_threads(2)
gen = pipeline("text-generation", model="sshleifer/tiny-gpt2", device=-1)
prompt = "Hello, please summarize: The quick brown fox jumps over the lazy dog."
times = []
for _ in range(50):
    s = time.time()
    gen(prompt, max_new_tokens=16, do_sample=False)
    times.append((time.time() - s) * 1000.0)

print("=" * 60)
print("LLM BASELINE LATENCY RESULTS")
print("=" * 60)
print(f"Requests: {len(times)}")
print(f"Avg Latency (ms): {round(statistics.mean(times), 2)}")
print(f"P50 Latency (ms): {round(sorted(times)[int(len(times)*0.5)], 2)}")
print(f"P95 Latency (ms): {round(sorted(times)[int(len(times)*0.95)-1], 2)}")
print(f"P99 Latency (ms): {round(sorted(times)[int(len(times)*0.99)-1], 2)}")
print("=" * 60)