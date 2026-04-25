"""
api.py
HRCompassAI — Flask REST API
Exposes all backend functionality (chat, admin, index) as JSON endpoints
so the React frontend can consume them.

Endpoints:
  GET  /api/health
  GET  /api/roles
  GET  /api/index-status
  POST /api/chat
  GET  /api/admin/documents
  POST /api/admin/upload
  DELETE /api/admin/document/<filename>
  POST /api/admin/rebuild
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from flask import Flask, request, jsonify
from flask_cors import CORS

# ── Import backend modules ────────────────────────────────────────────────────
from config import (
    ROLES,
    CONFIDENCE_THRESHOLD,
    DOCUMENTS_DIR,
    FAISS_INDEX_PATH,
    METADATA_STORE_PATH,
)
from embeddings import load_all_documents, build_chunk_records, load_metadata
from retriever import (
    load_index,
    build_index,
    index_exists,
    hybrid_search,
    is_answer_found,
    format_context,
)
from system_llm import generate_answer
from admin import (
    list_uploaded_documents,
    save_uploaded_file,
    delete_document,
    rebuild_index_from_documents,
)

# ── Flask App ─────────────────────────────────────────────────────────────────
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": ["http://localhost:5173", "http://localhost:3000"]}})

# ── In-memory index cache (loaded once per process) ───────────────────────────
_index = None
_chunk_records = []


def get_or_build_index():
    """Load the FAISS index into memory (or build it if not found)."""
    global _index, _chunk_records
    if _index is not None and _chunk_records:
        return _index, _chunk_records

    _chunk_records = load_metadata()
    _index = load_index()

    if _index is None or not _chunk_records:
        pages = load_all_documents()
        if pages:
            _chunk_records = build_chunk_records(pages)
            _index = build_index(_chunk_records)

    return _index, _chunk_records


def invalidate_index():
    """Force a reload on the next request."""
    global _index, _chunk_records
    _index = None
    _chunk_records = []


# ── Helper: safe UploadedFile wrapper for admin.py ───────────────────────────
class _UploadWrapper:
    """Adapter so Flask's FileStorage looks like Streamlit's UploadedFile."""
    def __init__(self, flask_file):
        self.name = flask_file.filename
        self._data = flask_file.read()

    def getbuffer(self):
        return self._data


# ═════════════════════════════════════════════════════════════════════════════
# ROUTES
# ═════════════════════════════════════════════════════════════════════════════

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "HRCompassAI"})


@app.route("/api/roles", methods=["GET"])
def roles():
    return jsonify({
        "roles": list(ROLES.keys()),
        "permissions": {k: v if v is not None else "__all__" for k, v in ROLES.items()},
    })


@app.route("/api/index-status", methods=["GET"])
def index_status():
    index, chunks = get_or_build_index()
    if index is None:
        return jsonify({"indexed": False, "vectorCount": 0, "documentCount": 0})

    doc_names = list({r["source"] for r in chunks})
    return jsonify({
        "indexed": True,
        "vectorCount": index.ntotal,
        "documentCount": len(doc_names),
        "documents": doc_names,
    })


@app.route("/api/chat", methods=["POST"])
def chat():
    body = request.get_json(force=True)
    query: str = (body.get("query") or "").strip()
    role: str = body.get("role", "Employee")

    if not query:
        return jsonify({"error": "query is required"}), 400

    index, chunk_records = get_or_build_index()

    if index is None or not chunk_records:
        return jsonify({
            "answer": "⚠️ No policy documents have been indexed yet. Please ask your HR administrator to upload documents.",
            "sources": [],
            "confidence": None,
            "found": False,
        })

    results = hybrid_search(query, index, chunk_records, role=role)

    if not is_answer_found(results):
        return jsonify({
            "answer": "This information is not available in the company policy documents.",
            "sources": [],
            "confidence": results[0]["confidence"] if results else 0.0,
            "found": False,
        })

    context = format_context(results)
    answer = generate_answer(query, results, context)
    top_confidence = results[0]["confidence"] if results else 0.0

    # Deduplicate and serialise sources
    seen = set()
    sources = []
    for r in results:
        key = f"{r['source']}|{r['page']}"
        if key not in seen:
            seen.add(key)
            sources.append({"source": r["source"], "page": r["page"]})

    return jsonify({
        "answer": answer,
        "sources": sources,
        "confidence": round(float(top_confidence), 4),
        "found": True,
    })


# ── Admin endpoints ───────────────────────────────────────────────────────────

@app.route("/api/admin/documents", methods=["GET"])
def admin_list_documents():
    docs = list_uploaded_documents()
    result = [
        {"name": d.name, "sizeKB": round(d.stat().st_size / 1024, 1)}
        for d in docs
    ]
    return jsonify({"documents": result})


@app.route("/api/admin/upload", methods=["POST"])
def admin_upload():
    if "files" not in request.files:
        return jsonify({"error": "No files part in request"}), 400

    uploaded = []
    for file in request.files.getlist("files"):
        if file.filename:
            wrapper = _UploadWrapper(file)
            dest = DOCUMENTS_DIR / wrapper.name
            with open(dest, "wb") as f:
                f.write(wrapper._data)
            uploaded.append(wrapper.name)

    # Invalidate cached index so next query triggers rebuild
    if FAISS_INDEX_PATH.exists():
        FAISS_INDEX_PATH.unlink()
    if METADATA_STORE_PATH.exists():
        METADATA_STORE_PATH.unlink()
    invalidate_index()

    return jsonify({"uploaded": uploaded, "message": f"{len(uploaded)} file(s) uploaded. Rebuild the index to apply."})


@app.route("/api/admin/document/<filename>", methods=["DELETE"])
def admin_delete_document(filename: str):
    target = DOCUMENTS_DIR / filename
    if not target.exists():
        return jsonify({"error": f"File '{filename}' not found"}), 404
    delete_document(filename)
    invalidate_index()
    return jsonify({"deleted": filename})


@app.route("/api/admin/rebuild", methods=["POST"])
def admin_rebuild():
    global _index, _chunk_records
    try:
        pages = load_all_documents()
        if not pages:
            return jsonify({"error": "No documents found to index"}), 400
        chunks = build_chunk_records(pages)
        _index = build_index(chunks)
        _chunk_records = chunks
        return jsonify({
            "success": True,
            "chunkCount": len(chunks),
            "vectorCount": _index.ntotal,
            "message": f"Index rebuilt with {len(chunks)} chunks from {len(pages)} pages.",
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ═════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("HRCompassAI API starting on http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
