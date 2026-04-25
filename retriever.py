"""
retriever.py
Handles:
  - Building and persisting the FAISS index
  - Hybrid search: semantic (FAISS) + keyword (BM25)
  - Role-based chunk filtering
  - Returning results with confidence scores
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

import faiss
import numpy as np
from rank_bm25 import BM25Okapi

from config import (
    EMBEDDING_DIMENSION,
    TOP_K,
    CONFIDENCE_THRESHOLD,
    DISTANCE_THRESHOLD,
    FAISS_INDEX_PATH,
    METADATA_STORE_PATH,
    ROLES,
)
from embeddings import embed_chunks, encode_query, load_metadata, save_metadata


# ── FAISS Index Management ─────────────────────────────────────────────────

def build_index(chunk_records: List[Dict[str, Any]]) -> faiss.Index:
    """
    Create a FAISS IndexFlatL2 from the given chunk records,
    save it to disk, and return the index object.
    """
    embeddings = embed_chunks(chunk_records)
    index = faiss.IndexFlatL2(EMBEDDING_DIMENSION)
    index.add(embeddings)  # type: ignore[arg-type]
    faiss.write_index(index, str(FAISS_INDEX_PATH))
    save_metadata(chunk_records)
    return index


def load_index() -> Optional[faiss.Index]:
    """Load a previously built FAISS index from disk, or return None."""
    if FAISS_INDEX_PATH.exists():
        return faiss.read_index(str(FAISS_INDEX_PATH))
    return None


def index_exists() -> bool:
    return FAISS_INDEX_PATH.exists() and METADATA_STORE_PATH.exists()


# ── Hybrid Search ──────────────────────────────────────────────────────────

def _semantic_search(
    query: str,
    index: faiss.Index,
    chunk_records: List[Dict[str, Any]],
    top_k: int,
) -> List[Tuple[Dict[str, Any], float]]:
    """
    Query FAISS index, returning a list of (chunk_record, confidence) tuples.
    confidence = 1 / (1 + L2_distance)  → range (0, 1], higher is better.
    Filters out results with distance > DISTANCE_THRESHOLD.
    """
    query_vec = encode_query(query)
    distances, indices = index.search(query_vec, top_k * 2)  # Get more candidates for filtering
    results = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx == -1:
            continue
        # Filter by distance threshold
        if dist > DISTANCE_THRESHOLD:
            continue
        confidence = float(1.0 / (1.0 + dist))
        results.append((chunk_records[idx], confidence))
        if len(results) >= top_k:
            break
    return results


def _bm25_search(
    query: str,
    chunk_records: List[Dict[str, Any]],
    top_k: int,
) -> List[Tuple[Dict[str, Any], float]]:
    """
    BM25 keyword search over chunk texts.
    Returns (chunk_record, normalised_bm25_score) tuples.
    """
    tokenised_corpus = [r["text"].lower().split() for r in chunk_records]
    bm25 = BM25Okapi(tokenised_corpus)
    scores = bm25.get_scores(query.lower().split())
    max_score = max(scores) if scores.max() > 0 else 1.0
    # Get top-k indices
    top_indices = np.argsort(scores)[::-1][:top_k]
    results = []
    for idx in top_indices:
        norm_score = float(scores[idx] / max_score)
        results.append((chunk_records[idx], norm_score))
    return results


def hybrid_search(
    query: str,
    index: faiss.Index,
    chunk_records: List[Dict[str, Any]],
    role: Optional[str] = None,
    top_k: int = TOP_K,
    semantic_weight: float = 0.7,
) -> List[Dict[str, Any]]:
    """
    Combine FAISS semantic search and BM25 keyword search results.
    Results are filtered by user role if provided, then ranked by combined score.

    Returns a list of result dicts with keys:
      text, source, page, chunk_index, category, confidence, rank
    """
    # Role-based filtering
    allowed_categories = None
    if role and ROLES.get(role) is not None:
        allowed_categories = set(ROLES[role])

    def allowed(record: Dict[str, Any]) -> bool:
        if allowed_categories is None:
            return True
        return record.get("category", "General") in allowed_categories

    filtered_records = [r for r in chunk_records if allowed(r)]
    if not filtered_records:
        return []

    # Re-index only the filtered records for FAISS search
    # (simple approach: search full index, then filter by source)
    sem_results = _semantic_search(query, index, chunk_records, top_k * 2)
    bm25_results = _bm25_search(query, filtered_records, top_k * 2)

    # Merge scores
    score_map: Dict[int, Dict] = {}
    for rec, score in sem_results:
        if not allowed(rec):
            continue
        key = id(rec)
        if key not in score_map:
            score_map[key] = {"record": rec, "sem": score, "bm25": 0.0}
        else:
            score_map[key]["sem"] = max(score_map[key]["sem"], score)

    for rec, score in bm25_results:
        key = id(rec)
        if key not in score_map:
            score_map[key] = {"record": rec, "sem": 0.0, "bm25": score}
        else:
            score_map[key]["bm25"] = max(score_map[key]["bm25"], score)

    bm25_weight = 1.0 - semantic_weight
    combined = []
    for key, data in score_map.items():
        combined_score = (semantic_weight * data["sem"]) + (bm25_weight * data["bm25"])
        combined.append((data["record"], combined_score))

    combined.sort(key=lambda x: x[1], reverse=True)
    top = combined[:top_k]

    results = []
    for rank, (rec, score) in enumerate(top, start=1):
        result = dict(rec)
        result["confidence"] = round(score, 4)
        result["rank"] = rank
        results.append(result)

    return results


def is_answer_found(results: List[Dict[str, Any]]) -> bool:
    """
    Return True only if the top result's confidence meets the threshold.
    """
    if not results:
        return False
    return results[0]["confidence"] >= CONFIDENCE_THRESHOLD


def format_context(results: List[Dict[str, Any]]) -> str:
    """Prepare context for LLM - use only top result truncated to avoid verbose answers."""
    if not results:
        return ""
    
    # Use only the top result to keep answers focused
    top_result = results[0]
    header = f"[Source: {top_result['source']}, Page {top_result['page']}]"
    
    # Truncate text to first 500 chars to avoid overwhelming the LLM with full chunks
    text = top_result['text'][:500]
    if len(top_result['text']) > 500:
        text = text.rsplit(' ', 1)[0] + '...'
    
    return f"{header}\n{text}"
