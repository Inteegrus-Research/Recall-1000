# src/database.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.config import DB_URL
from src.models import Base

_engine = None
_SessionLocal = None

def init_db():
    global _engine, _SessionLocal
    os.makedirs("data", exist_ok=True)
    _engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    Base.metadata.create_all(bind=_engine)

def get_db():
    global _SessionLocal
    if _SessionLocal is None:
        init_db()
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_session():
    global _SessionLocal
    if _SessionLocal is None:
        init_db()
    return _SessionLocal()