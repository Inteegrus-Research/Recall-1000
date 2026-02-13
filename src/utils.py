# src/utils.py
import re
import math
from typing import List, Tuple

def mask_sensitive(text: str) -> str:
    """Mask 16‑digit numbers and last‑4 digits; apply only to final response."""
    text = re.sub(r'\b\d{16}\b', '************', text)
    text = re.sub(r'\b(\d{12})(\d{4})\b', r'************\2', text)
    text = re.sub(r'(?<!\d)(\d{4})(?!\d)', '****', text)
    return text

def estimate_tokens(text: str) -> int:
    words = len(text.split())
    return max(1, int(words / 0.75))

def trunc_to_budget(items: List[Tuple[str, float]], budget: int, estimator) -> List[Tuple[str, float]]:
    kept = []
    used = 0
    for text, score in items:
        t = estimator(text)
        if used + t > budget:
            break
        kept.append((text, score))
        used += t
    return kept

def format_ms(ms: float) -> float:
    return round(ms, 2)

def recency_weight(current_turn: int, origin_turn: int) -> float:
    dt = max(0, current_turn - (origin_turn or current_turn))
    return math.exp(-dt / 200.0)