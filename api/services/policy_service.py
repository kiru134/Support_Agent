"""Hybrid policy retrieval: BM25 (lexical) + ChromaDB vector search (semantic,
Ollama-served embeddings), fused with Reciprocal Rank Fusion.

Why hybrid rather than either alone: BM25 is precise on exact terminology
("reschedule", "$10 fee") but misses paraphrase gaps; vector search closes those
gaps semantically but can drift on short, term-heavy policy queries where exact
wording matters (fee amounts, day counts). RRF combines both rankings without
needing to calibrate BM25 scores and cosine distances onto the same scale -- it only
needs each list's *rank order*, which is a natural fit for combining two
differently-scaled retrievers. See DECISIONS.md.

Both retrievers share the same underlying chunking (retrieval.py's PolicyIndex) and
the same stable chunk ids, which is what makes rank fusion by identity possible.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

import chromadb

from config.settings import settings
from retrieval import POLICY_DIR, PolicyIndex

EmbedFn = Callable[[list[str]], list[list[float]]]
RerankFn = Callable[[str, list[dict], int], list[dict]]


def _reciprocal_rank_fusion(
    ranked_lists: list[list[dict]], rrf_k: int, top_k: int
) -> list[dict]:
    """Each input list is pre-sorted best-first; items are dicts with at least
    "id". Returns fused results (deduped by id, richest dict kept) sorted by RRF
    score, best first."""
    scores: dict[str, float] = {}
    items: dict[str, dict] = {}
    for ranked in ranked_lists:
        for rank, item in enumerate(ranked):
            cid = item["id"]
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (rrf_k + rank + 1)
            # Keep whichever copy has more fields filled in (vector results don't
            # carry a BM25 lexical score and vice versa) -- doesn't affect ranking.
            if cid not in items or len(item) > len(items[cid]):
                items[cid] = item

    ordered_ids = sorted(scores, key=lambda cid: scores[cid], reverse=True)
    out = []
    for cid in ordered_ids[:top_k]:
        row = dict(items[cid])
        row["rrf_score"] = round(scores[cid], 4)
        out.append(row)
    return out


class PolicyService:
    COLLECTION_NAME = settings.chroma_collection_name

    def __init__(
        self,
        embed_fn: EmbedFn,
        persist_dir: Optional[str] = None,
        policy_dir: Path = POLICY_DIR,
        chroma_client: Optional["chromadb.ClientAPI"] = None,
        rerank_fn: Optional[RerankFn] = None,
    ):
        self.embed_fn = embed_fn
        self.rerank_fn = rerank_fn
        self.bm25_index = PolicyIndex(policy_dir)

        if chroma_client is not None:
            self.client = chroma_client
        elif persist_dir:
            self.client = chromadb.PersistentClient(path=persist_dir)
        else:
            self.client = chromadb.EphemeralClient()
        self.collection = self.client.get_or_create_collection(self.COLLECTION_NAME)
        self._index_if_empty()

    def _index_if_empty(self) -> None:
        if self.collection.count() > 0:
            return
        chunks = self.bm25_index.chunks
        ids = [c.id for c in chunks]
        docs = [c.text for c in chunks]
        metadatas = [{"doc": c.doc_id, "heading": c.heading} for c in chunks]
        embeddings = self.embed_fn(docs)
        self.collection.add(
            ids=ids, documents=docs, metadatas=metadatas, embeddings=embeddings
        )

    def _vector_search(self, query: str, k: int) -> list[dict]:
        [query_embedding] = self.embed_fn([query])
        result = self.collection.query(query_embeddings=[query_embedding], n_results=k)
        ids = result["ids"][0] if result["ids"] else []
        docs = result["documents"][0] if result["documents"] else []
        metas = result["metadatas"][0] if result["metadatas"] else []
        dists = result["distances"][0] if result["distances"] else []
        return [
            {
                "id": cid,
                "doc": meta["doc"],
                "heading": meta["heading"],
                "text": doc,
                "vector_score": round(1 - dist, 3),
            }
            for cid, doc, meta, dist in zip(ids, docs, metas, dists)
        ]

    def search(self, query: str, k: int = 4) -> list[dict]:
        # Floor, not just a ceiling: found during iteration (see ITERATION.md) that
        # the model sometimes requests k=1, which can starve it of a second chunk
        # it needed from the same doc (e.g. a doc's intro paragraph ranks first but
        # the specific numbers it asked about live in the next chunk down). Trust
        # the model's judgment on the ceiling, not on how narrow to go.
        k = max(settings.retrieval_min_k, min(6, k))
        bm25_results = self.bm25_index.search(query, k=settings.retrieval_bm25_k)
        vector_results = self._vector_search(query, k=settings.retrieval_vector_k)
        candidate_pool = max(k, settings.retrieval_rerank_candidates)
        fused = _reciprocal_rank_fusion(
            [bm25_results, vector_results], rrf_k=settings.retrieval_rrf_k, top_k=candidate_pool
        )

        if settings.retrieval_rerank_enabled and self.rerank_fn is not None:
            fused = self.rerank_fn(query, fused, k)
        else:
            fused = fused[:k]

        return [
            {
                "doc": r["doc"],
                "heading": r["heading"],
                "text": r["text"],
                "score": r.get("rrf_score", r.get("score", 0.0)),
            }
            for r in fused
        ]
