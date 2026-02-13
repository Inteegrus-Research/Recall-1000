# src/extractor.py
import re
from datetime import datetime
from typing import List, Tuple

MONTHS = "|".join(["January","February","March","April","May","June","July","August","September","October","November","December"])
STOP_NAMES = {"incorrect", "wrong", "false", "unknown", "error", "test"}

def _extract_language(text: str):
    m = re.search(r'(preferred language is|from now on,? please use|speak in|speak)\s+([A-Za-z]+)', text, re.I)
    return m.group(2).strip().capitalize() if m else None

def _extract_name(text: str):
    m = re.search(r'\b(Mr|Ms|Mrs|Dr)\.?\s+([A-Z][a-z]+)\b', text)
    if m and m.group(2).lower() not in STOP_NAMES:
        return m.group(2)
    m = re.search(r'\b(my name is|i am|this is)\s+([A-Z][a-z]+)\b', text, re.I)
    if m and m.group(2).lower() not in STOP_NAMES:
        return m.group(2)
    return None

def _extract_amount(text: str):
    m = re.search(r'\$\s?([0-9]+(?:\.[0-9]{1,2})?)', text)
    if m:
        return f"${m.group(1)}"
    m = re.search(r'([0-9]+(?:\.[0-9]{1,2})?)\s?(dollars|usd|inr|rs|rupees)', text, re.I)
    if m:
        return f"${m.group(1)}"
    return None

def _extract_due_date(text: str):
    m = re.search(r'\b(' + MONTHS + r')\s+(\d{1,2})(?:st|nd|rd|th)?\b', text, re.I)
    if m:
        return f"{m.group(1).capitalize()} {int(m.group(2))}"
    m = re.search(r'\b(\d{1,2})(?:st|nd|rd|th)?\s+(of\s+)?(' + MONTHS + r')\b', text, re.I)
    if m:
        return f"{m.group(3).capitalize()} {int(m.group(1))}"
    m = re.search(r'\b(\d{4}-\d{2}-\d{2})\b', text)
    if m:
        try:
            d = datetime.fromisoformat(m.group(1))
            return d.strftime("%B %d")
        except:
            return m.group(1)
    return None

def _extract_payment_status(text: str):
    tl = text.lower()
    if "already paid" in tl or "i paid" in tl or "payment processed" in tl:
        return "paid"
    if "dispute" in tl or "incorrect charge" in tl or "don't recognize" in tl:
        return "disputed"
    if "extension" in tl or "more time" in tl or "pay next week" in tl:
        return "extension_requested"
    return None

def _extract_call_time(text: str):
    m = re.search(r'(call me|call)\s+(after|at)?\s*(\d{1,2})(:\d{2})?\s*(am|pm)?', text, re.I)
    if m:
        hour = m.group(3)
        ampm = m.group(5) or ''
        return f"{hour}{ampm}".upper()
    return None

def _extract_account_info(text: str):
    m = re.search(r'account (?:ending in|no|number)[\s]*(\d{2,4})', text, re.I)
    if m:
        return f"account ending in {m.group(1)}"
    return None

def extract_memory_candidates(text: str, turn_id: int) -> List[Tuple[str, str, float]]:
    out = []
    lang = _extract_language(text)
    if lang:
        out.append(("language", lang, 0.98))
    name = _extract_name(text)
    if name:
        out.append(("customer_name", name, 0.95))
    amt = _extract_amount(text)
    if amt:
        out.append(("amount_due", amt, 0.97))
    due = _extract_due_date(text)
    if due:
        out.append(("due_date", due, 0.90))
    status = _extract_payment_status(text)
    if status:
        out.append(("payment_status", status, 0.95))
    ctime = _extract_call_time(text)
    if ctime:
        out.append(("call_time", ctime, 0.90))
    acct = _extract_account_info(text)
    if acct:
        out.append(("account_info", acct, 0.85))
    email = re.search(r'(\w+@\w+\.\w+)', text)
    if email:
        out.append(("email", email.group(1), 0.88))
    pref = re.search(r'\b(i like|i prefer|i love)\s+([a-zA-Z\s]{2,30})', text, re.I)
    if pref:
        out.append(("preference", pref.group(2).strip(), 0.70))
    return out