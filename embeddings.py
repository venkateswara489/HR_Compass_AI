"""
embeddings.py
Handles:
  - Loading documents (PDF, DOCX, TXT)
  - Splitting text into overlapping chunks
  - Generating embeddings using a local Sentence-Transformer model
"""
import json
import re
from pathlib import Path
from typing import List, Dict, Any

import numpy as np
import pdfplumber
import docx
from sentence_transformers import SentenceTransformer

from config import (
    EMBEDDING_MODEL_NAME,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    DOCUMENTS_DIR,
    METADATA_STORE_PATH,
)

# ── Lazy-loaded singleton model ────────────────────────────────────────────
_model: SentenceTransformer | None = None


def get_model() -> SentenceTransformer:
    """Return a cached SentenceTransformer, loading it only on first call."""
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _model


# ── Document Loaders ───────────────────────────────────────────────────────

def load_pdf(filepath: Path) -> List[Dict[str, Any]]:
    """Extract text from each page of a PDF, returning page-level records."""
    pages = []
    with pdfplumber.open(filepath) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            text = text.strip()
            if text:
                pages.append({
                    "text": text,
                    "source": filepath.name,
                    "page": page_num,
                    "category": _infer_category(filepath.name),
                })
    return pages


def load_docx(filepath: Path) -> List[Dict[str, Any]]:
    """Extract paragraphs from a DOCX file as a single page."""
    doc = docx.Document(str(filepath))
    text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    return [{
        "text": text,
        "source": filepath.name,
        "page": 1,
        "category": _infer_category(filepath.name),
    }]


def load_txt(filepath: Path) -> List[Dict[str, Any]]:
    """Load a plain-text file."""
    text = filepath.read_text(encoding="utf-8", errors="ignore").strip()
    return [{
        "text": text,
        "source": filepath.name,
        "page": 1,
        "category": "General",  # Will be overridden in build_chunk_records
    }]


def load_document(filepath: Path) -> List[Dict[str, Any]]:
    """Dispatch to the correct loader based on file extension."""
    suffix = filepath.suffix.lower()
    if suffix == ".pdf":
        return load_pdf(filepath)
    elif suffix in (".docx", ".doc"):
        return load_docx(filepath)
    elif suffix == ".txt":
        return load_txt(filepath)
    else:
        return []  # unsupported type


def load_all_documents(folder: Path = DOCUMENTS_DIR) -> List[Dict[str, Any]]:
    """Load every supported document in the given folder."""
    records = []
    for filepath in folder.iterdir():
        if filepath.is_file():
            records.extend(load_document(filepath))
    return records


# ── Chunking ───────────────────────────────────────────────────────────────

def chunk_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> List[str]:
    """
    Split *text* into overlapping fixed-size chunks (character-level).
    A hard sentence-boundary preference is applied by looking for the
    nearest sentence-end within a small tolerance window.
    """
    chunks: List[str] = []
    start = 0
    length = len(text)

    while start < length:
        end = min(start + chunk_size, length)

        # Try to break at a sentence boundary within ±50 chars of `end`
        if end < length:
            window = text[max(end - 50, start): min(end + 50, length)]
            match = None
            for m in re.finditer(r'[.!?]\s', window):
                match = m
            if match:
                end = max(end - 50, start) + match.end()

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        # Ensure start always advances to prevent infinite loop
        new_start = end - overlap
        if new_start <= start:
            new_start = start + 1  # Minimum advancement
        start = new_start

    return chunks


def build_chunk_records(pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Given page records (each with 'text', 'source', 'page', 'category'),
    split every page into overlapping chunks and tag each chunk with
    positional metadata. Infer category from chunk text for better role-based filtering.
    """
    chunk_records: List[Dict[str, Any]] = []
    for page in pages:
        chunks = chunk_text(page["text"])
        for i, chunk in enumerate(chunks):
            chunk_records.append({
                "text": chunk,
                "source": page["source"],
                "page": page["page"],
                "chunk_index": i,
                "category": _infer_category_from_text(chunk),
            })
    return chunk_records


# ── Embedding Generation ───────────────────────────────────────────────────

def embed_chunks(chunk_records: List[Dict[str, Any]]) -> np.ndarray:
    """
    Encode each chunk's text and return an (N, dim) float32 array
    suitable for a FAISS index.
    """
    model = get_model()
    texts = [r["text"] for r in chunk_records]
    embeddings = model.encode(texts, show_progress_bar=True, convert_to_numpy=True)
    return embeddings.astype(np.float32)


def encode_query(query: str) -> np.ndarray:
    """Encode a single user query into a (1, dim) float32 array."""
    model = get_model()
    vec = model.encode([query], convert_to_numpy=True)
    return vec.astype(np.float32)


# ── Metadata Persistence ───────────────────────────────────────────────────

def save_metadata(chunk_records: List[Dict[str, Any]], path: Path = METADATA_STORE_PATH) -> None:
    """Persist chunk records (text + source info) to JSON."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(chunk_records, f, ensure_ascii=False, indent=2)


def load_metadata(path: Path = METADATA_STORE_PATH) -> List[Dict[str, Any]]:
    """Load persisted chunk records from JSON."""
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ── Helpers ────────────────────────────────────────────────────────────────

def _infer_category_from_text(text: str) -> str:
    """
    Infer category from the chunk text based on section headers or keywords.
    """
    text_lower = text.lower()
    if "leave policy" in text_lower or "annual leave" in text_lower or "sick leave" in text_lower or "maternity" in text_lower or "paternity" in text_lower:
        return "Leave"
    if "code of conduct" in text_lower or "professional behaviour" in text_lower or "dress code" in text_lower or "conflict of interest" in text_lower or "confidentiality" in text_lower or "remote work policy" in text_lower or "work from home" in text_lower:
        return "Code of Conduct"
    if "benefits" in text_lower or "health insurance" in text_lower or "provident fund" in text_lower or "gratuity" in text_lower:
        return "Benefits"
    if "performance" in text_lower or "appraisals" in text_lower or "promotions" in text_lower or "pip" in text_lower:
        return "Performance"
    if "disciplinary" in text_lower or "termination" in text_lower or "suspension" in text_lower:
        return "Disciplinary"
    return "General"
