# src/models.py
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Float, Boolean, Text, Index

Base = declarative_base()

class MemoryFact(Base):
    __tablename__ = "memory_facts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    key = Column(String, index=True, nullable=False)
    value = Column(Text, nullable=False)
    category = Column(String, nullable=True)
    origin_turn = Column(Integer, nullable=False)
    last_accessed_turn = Column(Integer, nullable=True)
    access_count = Column(Integer, default=0)
    confidence = Column(Float, default=0.9)
    is_active = Column(Boolean, default=True, index=True)  # speed
    superseded_by = Column(Integer, nullable=True)
    root_id = Column(Integer, nullable=True)

    def to_dict(self):
        return {
            "memory_id": f"mem_{self.id:04d}",
            "content": f"{self.key}: {self.value}",
            "origin_turn": self.origin_turn,
            "last_used_turn": self.last_accessed_turn or self.origin_turn,
            "confidence": self.confidence
        }