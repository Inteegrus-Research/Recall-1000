# src/vector_store.py
import os
import pickle
import threading
import numpy as np
import faiss
from sklearn.feature_extraction.text import TfidfVectorizer
from src.config import EMBED_DIM, VECTOR_STORE_PATH

class VectorStore:
    def __init__(self, dim=EMBED_DIM, path=VECTOR_STORE_PATH):
        self.lock = threading.Lock()
        self.dim = dim
        self.path = path
        self.texts = []
        self.id_map = []
        self.vectorizer = TfidfVectorizer(
            max_features=dim,
            stop_words='english',
            lowercase=True,
            analyzer='word'
        )
        self.index = None
        self.is_fitted = False
        self.current_dim = None

        if os.path.exists(self.path):
            try:
                self._load()
            except Exception:
                # corrupted file -> reset cleanly
                self.texts = []
                self.id_map = []
                self.index = None
                self.is_fitted = False
                self.current_dim = None

    def _ensure_index(self):
        if not self.texts:
            self.index = None
            self.is_fitted = False
            self.current_dim = None
            return
        if not self.is_fitted:
            # fit vectorizer once on texts
            self.vectorizer.fit(self.texts)
            self.is_fitted = True
        # transform texts once
        X = self.vectorizer.transform(self.texts).toarray().astype(np.float32)
        faiss.normalize_L2(X)
        self.current_dim = X.shape[1]
        self.index = faiss.IndexFlatIP(self.current_dim)
        self.index.add(X)

    def add_memory(self, mem_id: int, text: str):
        with self.lock:
            if not self.is_fitted and self.texts:
                self._ensure_index()
            if not self.is_fitted:
                # first element: append then ensure index
                self.texts.append(text)
                self.id_map.append(mem_id)
                self._ensure_index()
            else:
                vec = self.vectorizer.transform([text]).toarray().astype(np.float32)
                # if new vector dim doesn't match current_dim, rebuild from texts
                if vec.shape[1] != self.current_dim:
                    self.texts.append(text)
                    self.id_map.append(mem_id)
                    self._ensure_index()
                else:
                    faiss.normalize_L2(vec)
                    self.texts.append(text)
                    self.id_map.append(mem_id)
                    # add vector to existing index efficiently
                    self.index.add(vec)
            # Save only metadata (vectorizer + texts + id_map)
            self._save()

    def rebuild_from_db(self, session):
        from src.models import MemoryFact
        with self.lock:
            active = session.query(MemoryFact).filter(MemoryFact.is_active == True).all()
            self.texts = [f"{m.key}: {m.value}" for m in active]
            self.id_map = [m.id for m in active]
            self.is_fitted = False
            self._ensure_index()
            self._save()

    def search(self, query: str, k: int = 5):
        with self.lock:
            if not self.texts or not self.is_fitted or self.index is None:
                return []
            qv = self.vectorizer.transform([query]).toarray().astype(np.float32)
            if qv.shape[1] != self.current_dim:
                # dimension mismatch unlikely; fallback empty
                return []
            faiss.normalize_L2(qv)
            n = min(k, self.index.ntotal)
            if n == 0:
                return []
            D, I = self.index.search(qv, n)
            results = []
            for score, idx in zip(D[0], I[0]):
                if idx < len(self.id_map):
                    results.append((self.id_map[idx], float(score)))
            return results

    def _save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "wb") as f:
            pickle.dump({
                "texts": self.texts,
                "id_map": self.id_map,
                "vectorizer": self.vectorizer,
                "is_fitted": self.is_fitted,
                "current_dim": self.current_dim
            }, f)

    def _load(self):
        with open(self.path, "rb") as f:
            data = pickle.load(f)
        self.texts = data.get("texts", [])
        self.id_map = data.get("id_map", [])
        self.vectorizer = data.get("vectorizer", self.vectorizer)
        # Force refit/ensure to maintain consistency
        self.is_fitted = False
        self._ensure_index()
