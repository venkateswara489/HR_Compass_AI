"""Document loading, chunking, and embedding utilities for HRCompassAI."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
import re

import docx
import numpy as np
import pdfplumber
from sentence_transformers import SentenceTransformer

from utils import clean_text


EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
DEFAULT_CHUNK_SIZE = 400
DEFAULT_CHUNK_OVERLAP = 50

_model: SentenceTransformer | None = None


def get_model(model_name: str = EMBEDDING_MODEL_NAME) -> SentenceTransformer:
    """Return a cached embedding model instance."""
    global _model
    if _model is None:
        _model = SentenceTransformer(model_name)
    return _model


def load_pdf(path: Path) -> List[Dict[str, Any]]:
    """Load PDF pages with page-level metadata."""
    rows: List[Dict[str, Any]] = []
    with pdfplumber.open(path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            text = clean_text(page.extract_text() or "")
            if text:
                rows.append({"text": text, "source": path.name, "page": page_num})
    return rows


def load_docx(path: Path) -> List[Dict[str, Any]]:
    """Load DOCX content as a single logical page."""
    doc = docx.Document(str(path))
    content = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    text = clean_text(content)
    if not text:
        return []
    return [{"text": text, "source": path.name, "page": 1}]


def load_txt(path: Path) -> List[Dict[str, Any]]:
    """Load TXT content as a single logical page."""
    text = clean_text(path.read_text(encoding="utf-8", errors="ignore"))
    if not text:
        return []
    return [{"text": text, "source": path.name, "page": 1}]


def load_document(path: Path) -> List[Dict[str, Any]]:
    """Dispatch loader by extension."""
    ext = path.suffix.lower()
    if ext == ".pdf":
        return load_pdf(path)
    if ext in {".docx", ".doc"}:
        return load_docx(path)
    if ext == ".txt":
        return load_txt(path)
    return []


def load_all_documents(documents_dir: Path) -> List[Dict[str, Any]]:
    """Load all supported files from the documents directory."""
    rows: List[Dict[str, Any]] = []
    if not documents_dir.exists():
        return rows
    for path in sorted(documents_dir.iterdir()):
        if path.is_file():
            rows.extend(load_document(path))
    return rows


def chunk_text(text: str, chunk_size: int = DEFAULT_CHUNK_SIZE, overlap: int = DEFAULT_CHUNK_OVERLAP) -> List[str]:
    """Split text into overlapping chunks with sentence-aware boundaries."""
    text = clean_text(text)
    if not text:
        return []

    chunks: List[str] = []
    start = 0
    text_len = len(text)
    while start < text_len:
        end = min(start + chunk_size, text_len)
        if end < text_len:
            window = text[max(start, end - 80): min(text_len, end + 80)]
            matches = list(re.finditer(r"[.!?]\s", window))
            if matches:
                end = max(start, end - 80) + matches[-1].end()
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= text_len:
            break
        start = max(start + 1, end - overlap)
    return chunks


def build_chunk_records(
    pages: List[Dict[str, Any]],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> List[Dict[str, Any]]:
    """Build chunk records with metadata mapping back to source page."""
    records: List[Dict[str, Any]] = []
    for page in pages:
        chunks = chunk_text(page["text"], chunk_size=chunk_size, overlap=overlap)
        for i, chunk in enumerate(chunks):
            records.append(
                {
                    "text": chunk,
                    "source": page["source"],
                    "page": page["page"],
                    "chunk_index": i,
                }
            )
    return records


def embed_texts(texts: List[str], model_name: str = EMBEDDING_MODEL_NAME) -> np.ndarray:
    """Encode texts into normalized float32 vectors."""
    if not texts:
        return np.array([], dtype=np.float32)
    model = get_model(model_name=model_name)
    vectors = model.encode(
        texts,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return vectors.astype(np.float32)


def embed_chunks(chunk_records: List[Dict[str, Any]], model_name: str = EMBEDDING_MODEL_NAME) -> np.ndarray:
    """Encode chunk records into embedding vectors."""
    return embed_texts([r["text"] for r in chunk_records], model_name=model_name)


def encode_query(query: str, model_name: str = EMBEDDING_MODEL_NAME) -> np.ndarray:
    """Encode a query string into one normalized vector."""
    return embed_texts([clean_text(query)], model_name=model_name)
