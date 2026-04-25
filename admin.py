"""
admin.py
Admin Panel utilities for HRCompassAI.
Called from app.py when the user switches to the Admin sidebar section.
Handles:
  - Uploading new policy documents (saving to disk)
  - Deleting documents
  - Triggering a full index rebuild
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import List

import streamlit as st

from config import DOCUMENTS_DIR, FAISS_INDEX_PATH, METADATA_STORE_PATH
from embeddings import load_all_documents, build_chunk_records
from retriever import build_index


# ── File Management ────────────────────────────────────────────────────────

def list_uploaded_documents() -> List[Path]:
    """Return sorted list of policy documents currently on disk."""
    return sorted(DOCUMENTS_DIR.iterdir()) if DOCUMENTS_DIR.exists() else []


def save_uploaded_file(uploaded_file) -> Path:
    """
    Accept a Streamlit UploadedFile object and write it to DOCUMENTS_DIR.
    Returns the saved file path.
    """
    dest = DOCUMENTS_DIR / uploaded_file.name
    with open(dest, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return dest


def delete_document(filename: str) -> None:
    """Delete a document by name and remove the FAISS index (forces rebuild)."""
    target = DOCUMENTS_DIR / filename
    if target.exists():
        target.unlink()
    _clear_index()


def _clear_index() -> None:
    """Remove the persisted FAISS index so the next query triggers a rebuild."""
    if FAISS_INDEX_PATH.exists():
        FAISS_INDEX_PATH.unlink()
    if METADATA_STORE_PATH.exists():
        METADATA_STORE_PATH.unlink()
    # also clear any cached index in session state
    if "faiss_index" in st.session_state:
        del st.session_state["faiss_index"]
    if "chunk_records" in st.session_state:
        del st.session_state["chunk_records"]


# ── Index Rebuild ──────────────────────────────────────────────────────────

def rebuild_index_from_documents() -> int:
    """
    Reload all documents, re-chunk, re-embed, rebuild FAISS index.
    Returns the number of chunks created.
    """
    pages = load_all_documents()
    chunks = build_chunk_records(pages)
    if chunks:
        index = build_index(chunks)
        st.session_state["faiss_index"] = index
        st.session_state["chunk_records"] = chunks
    return len(chunks)


# ── Streamlit Admin Panel UI ───────────────────────────────────────────────

def render_admin_panel() -> None:
    """Render the complete admin panel inside the Streamlit main area."""
    st.markdown("## 🔧 Admin Panel — Manage Policy Documents")
    st.info(
        "Only authorised HR administrators should be in this section. "
        "Changes will trigger an automatic index rebuild."
    )

    # ── Upload section ─────────────────────────────────────────────────────
    st.markdown("### 📤 Upload New Policy Documents")
    uploaded_files = st.file_uploader(
        "Upload PDF, DOCX, or TXT files",
        type=["pdf", "docx", "doc", "txt"],
        accept_multiple_files=True,
        key="admin_uploader",
    )
    if uploaded_files:
        for uf in uploaded_files:
            path = save_uploaded_file(uf)
            st.success(f"✅ Saved: **{path.name}**")
        _clear_index()
        st.warning("Index cleared — click **Rebuild Index** below to apply changes.")

    st.divider()

    # ── Existing documents ─────────────────────────────────────────────────
    docs = list_uploaded_documents()
    st.markdown(f"### 📂 Current Policy Documents ({len(docs)} files)")

    if not docs:
        st.info("No documents uploaded yet. Use the uploader above.")
    else:
        for doc in docs:
            col1, col2 = st.columns([4, 1])
            col1.markdown(f"📄 **{doc.name}** — {doc.stat().st_size / 1024:.1f} KB")
            if col2.button("🗑️ Delete", key=f"del_{doc.name}"):
                delete_document(doc.name)
                st.success(f"Deleted **{doc.name}**")
                st.rerun()

    st.divider()

    # ── Rebuild button ─────────────────────────────────────────────────────
    st.markdown("### ⚙️ Rebuild Vector Index")
    st.caption(
        "Run this after uploading or deleting documents. "
        "Large document sets may take a moment."
    )
    if st.button("🔄 Rebuild Index Now", type="primary", key="rebuild_btn"):
        with st.spinner("Processing documents and building FAISS index…"):
            try:
                n_chunks = rebuild_index_from_documents()
                st.success(f"✅ Index built successfully with **{n_chunks}** chunks.")
            except Exception as e:
                st.error(f"❌ Build failed: {e}")
