"""
Retrieval layer for the policy knowledge base.

Production note: the spec calls for PostgreSQL + pgvector with embedding-based retrieval.
This module keeps the exact same interface (retrieve(query, k) -> list[Chunk]) but uses a
dependency-free TF-IDF cosine-similarity index over the markdown files in /knowledge_base,
so retrieval works without a running Postgres+pgvector instance or an embeddings API key.
To upgrade: replace `_INDEX` construction with pgvector similarity search; keep
rag/security.py wrapping every retrieved chunk exactly the same way.
"""
import math
import re
from dataclasses import dataclass
from pathlib import Path

from app.config import BASE_DIR

KB_DIR = Path(BASE_DIR).parent / "knowledge_base"


@dataclass
class Chunk:
    doc_id: str
    text: str
    score: float


_SUFFIXES = ("ability", "ation", "ingly", "ed", "ing", "able", "ally", "es", "s")


def _stem(token: str) -> str:
    """Very light suffix stripping so 'cancel'/'cancelled'/'cancellable' share a stem.
    Not a real stemmer (e.g. Porter) - good enough for a small policy KB; swap for a
    real embedding model in production (see module docstring)."""
    stem = token
    for suf in _SUFFIXES:
        if len(stem) > len(suf) + 3 and stem.endswith(suf):
            stem = stem[: -len(suf)]
            break
    # collapse a doubled consonant left behind by suffix stripping (cancell -> cancel)
    if len(stem) >= 2 and stem[-1] == stem[-2] and stem[-1] not in "aeiou":
        stem = stem[:-1]
    return stem


def _tokenize(text: str) -> list[str]:
    return [_stem(t) for t in re.findall(r"[a-z0-9]+", text.lower())]


class TfidfIndex:
    def __init__(self, docs: dict[str, str]):
        self.docs = docs
        self.doc_tokens = {k: _tokenize(v) for k, v in docs.items()}
        self.df: dict[str, int] = {}
        for tokens in self.doc_tokens.values():
            for t in set(tokens):
                self.df[t] = self.df.get(t, 0) + 1
        self.n_docs = max(len(docs), 1)

    def _vector(self, tokens: list[str]) -> dict[str, float]:
        tf: dict[str, int] = {}
        for t in tokens:
            tf[t] = tf.get(t, 0) + 1
        vec = {}
        for t, count in tf.items():
            idf = math.log((self.n_docs + 1) / (self.df.get(t, 0) + 1)) + 1
            vec[t] = count * idf
        return vec

    @staticmethod
    def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
        common = set(a) & set(b)
        num = sum(a[t] * b[t] for t in common)
        da = math.sqrt(sum(v * v for v in a.values())) or 1e-9
        db = math.sqrt(sum(v * v for v in b.values())) or 1e-9
        return num / (da * db)

    def search(self, query: str, k: int = 3) -> list[Chunk]:
        q_vec = self._vector(_tokenize(query))
        scored = []
        for doc_id, tokens in self.doc_tokens.items():
            d_vec = self._vector(tokens)
            score = self._cosine(q_vec, d_vec)
            if score > 0:
                scored.append(Chunk(doc_id=doc_id, text=self.docs[doc_id], score=round(score, 4)))
        scored.sort(key=lambda c: c.score, reverse=True)
        return scored[:k]


def _load_docs() -> dict[str, str]:
    docs = {}
    if KB_DIR.exists():
        for p in sorted(KB_DIR.glob("*.md")):
            docs[p.stem] = p.read_text(encoding="utf-8")
    return docs


_INDEX = TfidfIndex(_load_docs())


def retrieve(query: str, k: int = 3) -> list[Chunk]:
    return _INDEX.search(query, k)
