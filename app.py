"""
app.py
HRCompassAI — Flask REST API
Exposes all backend functionality (chat, admin, index) as JSON endpoints
so the React frontend can consume them.
"""
from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, request, jsonify
from flask_cors import CORS

from config import (
    ROLES,
    DOCUMENTS_DIR,
    FAISS_INDEX_PATH,
    METADATA_STORE_PATH,
)
from embeddings import load_all_documents, build_chunk_records
from retriever import (
    load_faiss_index,
    load_metadata,
    retrieve_chunks,
    upsert_index,
    SIMILARITY_THRESHOLD,
    TOP_K,
    confidence_label,
)
from utils import (
    ask_ollama,
    build_context,
    build_strict_prompt,
    extract_unique_sources,
)


app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": ["http://localhost:5173", "http://localhost:3000"]}})

_index = None
_chunk_records = []

def get_or_build_index():
    global _index, _chunk_records
    if _index is not None and _chunk_records:
        return _index, _chunk_records

    _chunk_records = load_metadata(METADATA_STORE_PATH)
    _index = load_faiss_index(FAISS_INDEX_PATH)

    if _index is None or not _chunk_records:
        pages = load_all_documents(DOCUMENTS_DIR)
        if pages:
            _chunk_records = build_chunk_records(pages)
            _index = upsert_index(_chunk_records, FAISS_INDEX_PATH, METADATA_STORE_PATH)

    return _index, _chunk_records

def invalidate_index():
    global _index, _chunk_records
    _index = None
    _chunk_records = []

class _UploadWrapper:
    def __init__(self, flask_file):
        self.name = flask_file.filename
        self._data = flask_file.read()

    def getbuffer(self):
        return self._data

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
    # For now, we'll ignore the role filtering since retrieve_chunks doesn't support it directly in this version
    # The previous implementation had role filtering.

    if not query:
        return jsonify({"error": "query is required"}), 400

    index, chunk_records = get_or_build_index()

    if index is None or not chunk_records:
        return jsonify({
            "answer": "⚠️ No policy documents have been indexed yet. Please ask your HR administrator to upload documents.",
            "sources": [],
            "confidence": 0.0,
            "found": False,
        })

    retrieved = retrieve_chunks(
        query=query,
        index=index,
        chunk_records=chunk_records,
        top_k=TOP_K,
        threshold=SIMILARITY_THRESHOLD,
    )

    if not retrieved:
        return jsonify({
            "answer": "This information is not available in the company policy documents.",
            "sources": [],
            "confidence": 0.0,
            "found": False,
        })

    context = build_context(retrieved, max_chars=1200)

    # Use system_llm for Ollama-based answer generation
    from system_llm import generate_answer
    try:
        answer = generate_answer(query, retrieved, context)
    except Exception:
        return jsonify({
            "answer": "The answer service is temporarily unavailable. Please try again later.",
            "sources": [],
            "confidence": 0.0,
            "found": False,
        }), 503

    if answer.startswith("Error:") or "could not connect" in answer.lower() or "timed out" in answer.lower():
        return jsonify({
            "answer": "The answer service is temporarily unavailable. Please try again later.",
            "sources": [],
            "confidence": 0.0,
            "found": False,
        }), 503

    if "not available in policy" in answer.lower():
        answer = "This information is not available in the company policy documents."

    top_confidence = float(retrieved[0].get("confidence", retrieved[0]["similarity"]))
    sources = [{"source": src, "page": page} for src, page in extract_unique_sources(retrieved)]

    return jsonify({
        "answer": answer,
        "sources": sources,
        "confidence": round(top_confidence, 4),
        "found": True,
    })

@app.route("/api/admin/documents", methods=["GET"])
def admin_list_documents():
    docs = sorted(DOCUMENTS_DIR.iterdir()) if DOCUMENTS_DIR.exists() else []
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
    target.unlink()
    
    if FAISS_INDEX_PATH.exists():
        FAISS_INDEX_PATH.unlink()
    if METADATA_STORE_PATH.exists():
        METADATA_STORE_PATH.unlink()
    invalidate_index()
    
    return jsonify({"deleted": filename})

@app.route("/api/admin/rebuild", methods=["POST"])
def admin_rebuild():
    global _index, _chunk_records
    try:
        pages = load_all_documents(DOCUMENTS_DIR)
        if not pages:
            return jsonify({"error": "No documents found to index"}), 400
        chunks = build_chunk_records(pages)
        _index = upsert_index(chunks, FAISS_INDEX_PATH, METADATA_STORE_PATH)
        _chunk_records = chunks
        return jsonify({
            "success": True,
            "chunkCount": len(chunks),
            "vectorCount": _index.ntotal,
            "message": f"Index rebuilt with {len(chunks)} chunks from {len(pages)} pages.",
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    print("HRCompassAI API starting on http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)

