# demo_payment.py
"""
Demonstrates the system on the 4 official payment reminder scripts.
Run this AFTER the API is running (./run_demo.sh).
"""
import requests
import time
import json

BASE = "http://127.0.0.1:8000"
USER_ID = "payment_demo"
turn = 1

def chat(message, expected_facts=None):
    global turn
    payload = {"user_id": USER_ID, "message": message, "turn_id": turn}
    start = time.time()
    resp = requests.post(f"{BASE}/chat", json=payload)
    elapsed = (time.time() - start) * 1000
    data = resp.json()
    print(f"\n--- Turn {turn} ---")
    print(f"Q: {message}")
    print(f"Latency: {elapsed:.1f} ms")
    print(f"A: {data['response']}")
    if data['active_memories']:
        print("Memories stored/updated:")
        for m in data['active_memories']:
            print(f"  - {m['content']} (conf: {m['confidence']})")
    turn += 1
    return data

print("="*60)
print("PAYMENT REMINDER DEMO (4 official scenarios)")
print("="*60)

# ---- 1. Friendly Reminder ----
chat("Hello, am I speaking with Mr. Johnson?")
chat("Yes, this is Johnson speaking.")
chat("Good afternoon, this is Sarah calling from ABC Financial. How are you?")
chat("I'm doing fine. How can I help you?")
chat("I'm calling about your account ending in 4582. Your payment of $450 was due on February 5th. It hasn't been processed yet.")
chat("Oh, I completely forgot! I've been so busy.")
chat("Would you like to make the payment now or set up a date?")
chat("I can make the payment right now.")
chat("Perfect, I'm processing $450. You'll get a confirmation email.")

# ---- 2. Extension Request ----
chat("Hello, this is Sarah again. You previously requested an extension?")
chat("Yes, I need more time – can I pay next week?")
chat("Of course, I've noted that. Your new due date is February 12th.")

# ---- 3. Dispute ----
chat("Hi, I'm calling about a charge on my account.")
chat("I see a payment of $450 that I don't recognize. This is incorrect.")
chat("I apologize for the confusion, let me investigate. I've marked this as disputed.")

# ---- 4. Already Paid ----
chat("Hello, I received a reminder but I already paid this bill.")
chat("Let me check your account... Yes, I see the payment processed yesterday. Thank you.")

# ---- Verify Memory Recall ----
print("\n" + "="*60)
print("VERIFYING MEMORY RETRIEVAL")
print("="*60)
chat("What is my name?")               # should return "Johnson"
chat("What was the due amount?")       # should return "$450"
chat("What is the status of my payment?")  # should return "paid" (from last scenario)
chat("Can you call me tomorrow?")      # should recall language (if set) – not in this demo, but structure works

print("\n✅ Payment demo completed. Check /debug/memory for full state.")
