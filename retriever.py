"""FAISS storage and retrieval layer for HRCompassAI."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple
import json

import faiss
import numpy as np

from embeddings import encode_query, embed_chunks


TOP_K = 2
SIMILARITY_THRESHOLD = 0.20


def save_metadata(chunk_records: List[Dict[str, Any]], metadata_path: Path) -> None:
    """Persist chunk metadata as JSON."""
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    with metadata_path.open("w", encoding="utf-8") as f:
        json.dump(chunk_records, f, ensure_ascii=False, indent=2)


def load_metadata(metadata_path: Path) -> List[Dict[str, Any]]:
    """Load metadata from disk."""
    if not metadata_path.exists():
        return []
    with metadata_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def build_faiss_index(chunk_records: List[Dict[str, Any]]) -> faiss.Index:
    """Build a cosine-similarity FAISS index from chunk records."""
    vectors = embed_chunks(chunk_records)
    if vectors.size == 0:
        raise ValueError("No chunk embeddings available to build index.")

    dim = vectors.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(vectors)
    return index


def save_faiss_index(index: faiss.Index, index_path: Path) -> None:
    """Write FAISS index to disk."""
    index_path.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(index_path))


def load_faiss_index(index_path: Path) -> faiss.Index | None:
    """Load FAISS index if present."""
    if not index_path.exists():
        return None
    return faiss.read_index(str(index_path))


def upsert_index(
    chunk_records: List[Dict[str, Any]],
    index_path: Path,
    metadata_path: Path,
) -> faiss.Index:
    """Build and persist index + metadata."""
    index = build_faiss_index(chunk_records)
    save_faiss_index(index, index_path)
    save_metadata(chunk_records, metadata_path)
    return index


def retrieve_chunks(
    query: str,
    index: faiss.Index,
    chunk_records: List[Dict[str, Any]],
    top_k: int = TOP_K,
    threshold: float = SIMILARITY_THRESHOLD,
) -> List[Dict[str, Any]]:
    """Retrieve relevant chunks with similarity filtering and normalized confidence."""
    q_vec = encode_query(query)
    search_k = min(max(top_k * 4, top_k), len(chunk_records))
    scores, indices = index.search(q_vec, search_k)

    results: List[Dict[str, Any]] = []
    seen_keys: set[Tuple[str, int, int]] = set()
    for score, idx in zip(scores[0], indices[0]):
        if idx < 0:
            continue
        similarity = float(score)
        if similarity < threshold:
            continue
        row = chunk_records[idx]
        key = (row["source"], int(row["page"]), int(row.get("chunk_index", 0)))
        if key in seen_keys:
            continue
        seen_keys.add(key)
        # Normalize confidence to 0-100% range
        confidence = max(0, min(100, int(similarity * 100)))
        results.append(
            {
                "text": row["text"],
                "source": row["source"],
                "page": row["page"],
                "chunk_index": row.get("chunk_index", 0),
                "similarity": similarity,
                "confidence": confidence / 100.0,  # Keep as decimal for internal use
            }
        )
        if len(results) >= top_k:
            break
    return results


def confidence_label(similarity: float) -> str:
    """Map similarity score to High/Medium/Low."""
    if similarity >= 0.65:
        return "High"
    if similarity >= 0.45:
        return "Medium"
    return "Low"
