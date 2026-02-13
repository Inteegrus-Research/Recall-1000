
# Recall-1000: Long-Form Memory for 1,000+ Turns

**NeuroHack 2026 | IITG.ai × Smallest.ai**
**Team:** அப்பாவிகள் 🥺
**Contact:** [24ec069@kpriet.ac.in](mailto:24ec069@kpriet.ac.in)
**Submission Date:** 12 February 2026

---

## Submission package

```
.
├── README.md
├── requirements.txt
├── run_demo.sh
├── test_core.py
├── stress_test_1000.py
├── latency_breakdown.py
├── demo_payment.py
├── persistence_test.py
├── api_latency_test.py
├── llm_baseline_test.py
├── main.py
└── src/
    ├── __init__.py
    ├── config.py
    ├── database.py
    ├── models.py
    ├── utils.py
    ├── vector_store.py
    ├── extractor.py
    └── memory_engine.py
# data/ is created at runtime
```

---
## Executive Summary

Large Language Models forget early-turn information due to limited context windows. Real-world conversational agents require persistent, accurate, low-latency long-term memory.

**Recall-1000** is a hybrid structured + semantic memory engine designed to:

* Persist high-value facts across 1000+ turns
* Retrieve relevant memory in sub-200ms P95 internal latency
* Minimize hallucination via deterministic extraction
* Provide reproducible evaluation metrics

This system is fully self-contained and benchmarked using 1000-turn stress testing.

---

# Final Measured Performance (1000 Turns)

## Stress Test (`./run_demo.sh`)

```
RESULTS (1000 turns)
======================================================================
Explicit Recall@3:        94.19%
Implicit Presence@5:      100.00%
Precision@3:              94.19%
MRR:                      0.9419
False Positive@3 Rate:    3.97%

Avg Latency (ms):         128.61
P50 Latency:              108.25
P95 Latency:              195.09
P99 Latency:              263.03
======================================================================
```

### Interpretation

*  Explicit Recall@3 = **94.19%**
*  Implicit Recall = **100%**
*  Precision@3 = **94.19%**
*  False Positive Rate = **3.97%**
*  MRR = **0.9419**

### Latency (Internal Retrieval Only)

* Avg = **128.61 ms**
* P95 = **195.09 ms**
* P99 = **263.03 ms**

This demonstrates scalable memory retrieval across 1000 turns with strong stability.

---

##  Component Microbenchmarks

```
Extraction (ms):
  mean: 0.856
  p50:  0.754
  p95:  0.844

Search (ms):
  mean: 21.647
  p50:  21.365
  p95:  25.325
```

* Fact extraction is sub-1ms.
* Vector search averages ~21ms.
* Deterministic fast-path reduces tail latency.

---

##  Persistence Validation

After simulated restart:

```
Vector search after reload:
[(57, 0.7071068286895752), (58, 0.0), (53, 0.0)]
```

This confirms:

* Vector index reload works.
* SQLite memory remains intact.
* Retrieval is consistent post-restart.

---

##  End-to-End API Latency

```
END-TO-END API LATENCY RESULTS
============================================================
Requests: 100
Avg Latency (ms): 243.36
P50 Latency (ms): 220.69
P95 Latency (ms): 331.75
P99 Latency (ms): 499.66
============================================================
```

### Interpretation

* Average API latency: **243.36 ms**
* P95: **331.75 ms**
* P99: **499.66 ms**

> End-to-end includes HTTP overhead and full request handling.
> Memory retrieval itself remains significantly faster (see stress test).

---

# Hackathon Criteria Alignment

### 🔹 Long-Range Memory Recall — Strong

* 94.19% Recall@3 across 1000 turns
* 100% implicit presence
* Structured deterministic extraction

### 🔹 Accuracy & Stability — Strong

* Precision@3 = 94.19%
* MRR = 0.9419
* Low 3.97% FP rate

### 🔹 Latency Impact — Strong

* Internal P95 < 200ms
* API P95 ≈ 332ms
* Sub-1ms extraction

### 🔹 Hallucination Avoidance — Controlled

* Deterministic extraction
* Confidence gating
* Active-only retrieval logic

### 🔹 Engineering Clarity

* Hybrid deterministic + semantic architecture
* Persistent vector index
* Fully reproducible benchmark harness

---

# System Architecture

1. User message → Rule-based extractor
2. Structured facts stored in SQLite
3. TF-IDF vectors stored in FAISS
4. Retrieval stack:

   * Deterministic fast-path
   * Intent-to-key mapping
   * Fuzzy key match
   * Vector fallback (recency-weighted)
5. Token-aware context injection

---

# How to Reproduce

### Setup

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Run full benchmark

```bash
chmod +x run_demo.sh
./run_demo.sh
```

### Conversation Demo

```bash
#run this in another terminal while pipeline running
python demo_payment.py
```

### API latency test

```bash
#run this in another terminal while pipeline running
python api_latency_test.py
```

### Clean run

```bash
rm -rf data/ && mkdir -p data
```

---

# Known Limitations

* English-only extraction patterns
* Rule-based extractor limits paraphrase generalization
* SQLite optimized for single-instance usage
* No distributed scaling layer (by design for hackathon scope)

---

# Final Summary

Recall-1000 achieves:

* 94.19% recall across 1000 turns
* 100% implicit memory presence
* Sub-200ms P95 internal latency
* ~243ms average API latency
* Persistent storage across restarts
* Fully reproducible evaluation

The system demonstrates scalable, low-hallucination conversational memory suitable for long-form dialogue agents.

---
