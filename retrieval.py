"""Stdlib-only lexical retrieval over the 12 Sezzle policy docs.

No sklearn / embeddings / vector DB: the corpus is ~7KB across 12 files, small
enough that a hand-rolled BM25 over heading-level chunks is both sufficient and
cheaper/faster than an embedding call at "100k questions/day" scale (see
DECISIONS.md). This module is exercised as a tool the model calls on demand
(`search_policy`), not stuffed into every prompt.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from pathlib import Path

POLICY_DIR = Path(__file__).parent / "sezzleaiengineertakehomechallenge"

# Query-side synonym expansion: shoppers phrase things differently than the policy
# docs do. Cheap and inspectable at this corpus size -- closes the exact lexical gaps
# observed in the visible golden cases (e.g. v03 "push back the payment date" vs.
# POLICY-02's "move an upcoming installment's due date") without reaching for
# embeddings.
SYNONYMS = {
    "push": "reschedule move",
    "delay": "reschedule move",
    "postpone": "reschedule move",
    "move": "reschedule",
    "change": "reschedule",
    "shipped": "dispute delivery",
    "never": "dispute",
    "receive": "dispute delivery",
    "limit": "limit spending credit",
    "declined": "decline limit",
    "decline": "decline limit",
    "job": "hardship",
    "lost": "hardship",
    "fired": "hardship",
    "afford": "hardship",
    "missed": "failed missed",
    "interest": "fees interest",
    "stolen": "fraud security",
    "hacked": "fraud security",
    "didn't": "fraud unauthorized",
    "unauthorized": "fraud security",
    "money": "refund",
    "return": "refund returns",
    "returned": "refund returns",
    "approved": "refund returns",
    "credit": "sezzle up credit reporting",
    "score": "sezzle up credit reporting",
}

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def _expand_query(text: str) -> list[str]:
    tokens = _tokenize(text)
    expanded = list(tokens)
    for tok in tokens:
        if tok in SYNONYMS:
            expanded.extend(_tokenize(SYNONYMS[tok]))
    return expanded


class Chunk:
    __slots__ = ("doc_id", "heading", "text", "tokens", "id")

    def __init__(self, doc_id: str, heading: str, text: str):
        self.doc_id = doc_id
        self.heading = heading
        self.text = text
        self.tokens = _tokenize(f"{heading} {text}")
        self.id = ""  # assigned once the full chunk list is known, see PolicyIndex.__init__


class PolicyIndex:
    def __init__(self, policy_dir: Path = POLICY_DIR):
        self.chunks: list[Chunk] = []
        for path in sorted(policy_dir.glob("POLICY_-*.md")):
            self.chunks.extend(self._chunk_doc(path))
        # Stable id per chunk, in the same "{doc_id}::{global_index}" scheme used
        # when indexing these same chunks into Chroma (see PolicyService) -- this is
        # what lets hybrid search fuse BM25 and vector result sets by identity.
        for i, c in enumerate(self.chunks):
            c.id = f"{c.doc_id}::{i}"

        self.N = len(self.chunks)
        self.avgdl = sum(len(c.tokens) for c in self.chunks) / max(1, self.N)
        self.df: Counter = Counter()
        for c in self.chunks:
            for term in set(c.tokens):
                self.df[term] += 1

    @staticmethod
    def _doc_id(path: Path) -> str:
        # e.g. "POLICY_-_01-payment-schedules.md" -> "01-payment-schedules"
        stem = path.stem.replace("POLICY_-_", "").replace("POLICY_-", "")
        return stem

    def _chunk_doc(self, path: Path) -> list[Chunk]:
        doc_id = self._doc_id(path)
        text = path.read_text()
        lines = text.splitlines()
        title = lines[0].lstrip("# ").strip() if lines else doc_id

        chunks: list[Chunk] = []
        heading = title
        buf: list[str] = []

        def flush():
            body = "\n".join(buf).strip()
            if body:
                chunks.append(Chunk(doc_id, heading, body))

        for line in lines[1:]:
            if line.startswith("##"):
                flush()
                heading = line.lstrip("# ").strip()
                buf = []
            elif line.strip() == "" and buf and not buf[-1].strip().startswith(("-", "|")):
                # blank line after a prose paragraph (not mid-list/table) -> new chunk
                flush()
                buf = []
            else:
                buf.append(line)
        flush()

        if not chunks:
            chunks.append(Chunk(doc_id, title, text.strip()))
        return chunks

    def _bm25(self, query_tokens: list[str], chunk: Chunk, k1=1.5, b=0.75) -> float:
        tf = Counter(chunk.tokens)
        dl = len(chunk.tokens)
        score = 0.0
        for term in query_tokens:
            f = tf.get(term, 0)
            if f == 0:
                continue
            df = self.df.get(term, 0)
            idf = math.log((self.N - df + 0.5) / (df + 0.5) + 1)
            denom = f + k1 * (1 - b + b * dl / max(1, self.avgdl))
            score += idf * (f * (k1 + 1)) / denom
        return score

    def search(self, query: str, k: int = 4) -> list[dict]:
        k = max(1, min(6, k))
        query_tokens = _expand_query(query)
        scored = [(self._bm25(query_tokens, c), c) for c in self.chunks]
        scored = [(s, c) for s, c in scored if s > 0]
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [
            {"id": c.id, "doc": c.doc_id, "heading": c.heading, "text": c.text, "score": round(s, 3)}
            for s, c in scored[:k]
        ]


_INDEX: PolicyIndex | None = None


def get_index() -> PolicyIndex:
    global _INDEX
    if _INDEX is None:
        _INDEX = PolicyIndex()
    return _INDEX


def search_policy(query: str, k: int = 4) -> list[dict]:
    return get_index().search(query, k)
