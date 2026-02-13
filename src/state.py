# src/state.py
import json
from src.models import MemoryFact

STATE_KEY = "__conv_state__"

class ConversationState:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.intent = None
        self.payment_status = None
        self.customer_name = None
        self.amount_due = None
        self.due_date = None
        self.turn_count = 0

    def update_from_message(self, message: str):
        msg = message.lower()
        if "dispute" in msg or "incorrect" in msg:
            self.intent = "dispute"
        elif "extension" in msg or "more time" in msg or "pay next week" in msg:
            self.intent = "extension"
        elif "already paid" in msg or "i paid" in msg:
            self.intent = "already_paid"
            self.payment_status = "paid"
        elif "call" in msg or "remind" in msg or "payment reminder" in msg:
            self.intent = "friendly_reminder"
        self.turn_count += 1

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "intent": self.intent,
            "payment_status": self.payment_status,
            "customer_name": self.customer_name,
            "amount_due": self.amount_due,
            "due_date": self.due_date,
            "turn_count": self.turn_count
        }

    @classmethod
    def from_dict(cls, d):
        state = cls(d.get("user_id", ""))
        state.intent = d.get("intent")
        state.payment_status = d.get("payment_status")
        state.customer_name = d.get("customer_name")
        state.amount_due = d.get("amount_due")
        state.due_date = d.get("due_date")
        state.turn_count = d.get("turn_count", 0)
        return state

def load_state_for_user(db, user_id: str):
    mem = db.query(MemoryFact).filter(
        MemoryFact.user_id == user_id,
        MemoryFact.key == STATE_KEY,
        MemoryFact.is_active == True
    ).order_by(MemoryFact.last_accessed_turn.desc()).first()
    if not mem:
        return ConversationState(user_id)
    try:
        return ConversationState.from_dict(json.loads(mem.value))
    except:
        return ConversationState(user_id)

def save_state_for_user(db, user_id: str, state: ConversationState, turn_id: int):
    old_list = db.query(MemoryFact).filter(
        MemoryFact.user_id == user_id,
        MemoryFact.key == STATE_KEY,
        MemoryFact.is_active == True
    ).all()
    for o in old_list:
        o.is_active = False
        db.add(o)
    mem = MemoryFact(
        user_id=user_id,
        key=STATE_KEY,
        value=json.dumps(state.to_dict()),
        category="state",
        origin_turn=turn_id,
        last_accessed_turn=turn_id,
        confidence=0.99,
        is_active=True
    )
    db.add(mem)
    db.commit()
    return mem