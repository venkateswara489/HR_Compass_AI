"""
app.py
HRCompassAI — Main Streamlit Application
Features:
  - Chat interface with history
  - Role-Based Access Control
  - Hybrid FAISS + BM25 retrieval
  - Source/page attribution
  - Confidence score display
  - No-answer fallback
  - 👍/👎 feedback
  - Admin panel (HR role only)
"""
import json
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

import streamlit as st

# ── Page config (MUST be first Streamlit call) ─────────────────────────────
st.set_page_config(
    page_title="HRCompassAI — Policy Assistant",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)

from config import ROLES, CONFIDENCE_THRESHOLD
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
from admin import render_admin_panel

# ── Custom CSS ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
  /* ── Google Fonts ── */
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

  /* ── Background ── */
  .stApp { background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%); }

  /* ── Sidebar ── */
  section[data-testid="stSidebar"] {
    background: rgba(255,255,255,0.05) !important;
    backdrop-filter: blur(16px);
    border-right: 1px solid rgba(255,255,255,0.1);
  }
  section[data-testid="stSidebar"] * { color: #e0e0ff !important; }

  /* ── Cards / containers ── */
  .hr-card {
    background: rgba(255,255,255,0.07);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 16px;
    padding: 1.4rem 1.6rem;
    margin-bottom: 1rem;
    backdrop-filter: blur(10px);
    transition: box-shadow 0.2s;
  }
  .hr-card:hover { box-shadow: 0 0 20px rgba(130,100,255,0.3); }

  /* ── Chat bubbles ── */
  .chat-user {
    background: linear-gradient(135deg, #6c63ff, #9b59b6);
    color: #fff;
    border-radius: 18px 18px 4px 18px;
    padding: 0.85rem 1.1rem;
    margin: 0.4rem 0;
    max-width: 82%;
    margin-left: auto;
    box-shadow: 0 4px 14px rgba(108,99,255,0.4);
    font-size: 0.95rem;
  }
  .chat-bot {
    background: rgba(255,255,255,0.09);
    border: 1px solid rgba(255,255,255,0.14);
    color: #e8e8ff;
    border-radius: 18px 18px 18px 4px;
    padding: 0.85rem 1.1rem;
    margin: 0.4rem 0;
    max-width: 90%;
    font-size: 0.95rem;
  }

  /* ── Source badge ── */
  .source-badge {
    display: inline-block;
    background: rgba(108,99,255,0.25);
    border: 1px solid rgba(108,99,255,0.5);
    color: #b0a8ff;
    border-radius: 8px;
    padding: 0.2rem 0.6rem;
    font-size: 0.78rem;
    margin: 0.2rem 0.2rem 0 0;
  }

  /* ── Confidence bar ── */
  .confidence-wrap { margin: 0.5rem 0 0.2rem; }
  .confidence-label { font-size: 0.78rem; color: #9090bb; margin-bottom: 4px; }

  /* ── Logo / title ── */
  .logo-title {
    font-size: 1.8rem;
    font-weight: 700;
    background: linear-gradient(90deg, #a78bfa, #60a5fa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    line-height: 1.2;
  }
  .logo-sub { color: #9090cc; font-size: 0.85rem; margin-top: 0.2rem; }

  /* ── Input area ── */
  .stTextInput > div > div > input {
    background: rgba(255,255,255,0.08) !important;
    border: 1px solid rgba(255,255,255,0.2) !important;
    border-radius: 12px !important;
    color: #fff !important;
    padding: 0.75rem 1rem !important;
  }
  .stTextInput > div > div > input:focus {
    border-color: #7c6dff !important;
    box-shadow: 0 0 0 2px rgba(124,109,255,0.3) !important;
  }

  /* ── Buttons ── */
  .stButton > button {
    border-radius: 10px !important;
    background: linear-gradient(135deg, #6c63ff, #9b59b6) !important;
    color: #fff !important;
    border: none !important;
    font-weight: 500 !important;
    transition: transform 0.15s, box-shadow 0.15s !important;
  }
  .stButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 20px rgba(108,99,255,0.5) !important;
  }

  /* ── Dividers ── */
  hr { border-color: rgba(255,255,255,0.1) !important; }

  /* ── Feedback buttons ── */
  .feedback-row { display: flex; gap: 0.5rem; margin-top: 0.6rem; }
</style>
""", unsafe_allow_html=True)


# ── Session State Initialisation ────────────────────────────────────────────

def init_state() -> None:
    defaults = {
        "chat_history": [],        # list of dicts {role, content, sources, confidence}
        "faiss_index": None,
        "chunk_records": [],
        "selected_role": "Employee",
        "feedback_log": [],        # list of {question, helpful: bool}
        "index_built": False,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


init_state()


# ── Index Loading / Building ────────────────────────────────────────────────

@st.cache_resource(show_spinner=False)
def get_or_build_index():
    """Load existing FAISS index or build one from the documents folder."""
    chunk_records = load_metadata()
    index = load_index()
    if index is None or not chunk_records:
        pages = load_all_documents()
        if not pages:
            return None, []
        chunk_records = build_chunk_records(pages)
        index = build_index(chunk_records)
    return index, chunk_records


# ── Sidebar ────────────────────────────────────────────────────────────────

def render_sidebar() -> None:
    with st.sidebar:
        # Logo
        st.markdown('<p class="logo-title">🧭 HRCompassAI</p>', unsafe_allow_html=True)
        st.markdown('<p class="logo-sub">Policy-Grounded HR Assistant</p>', unsafe_allow_html=True)
        st.divider()

        # Role selector
        st.markdown("**👤 Select Your Role**")
        role = st.radio(
            label="Role",
            options=list(ROLES.keys()),
            index=list(ROLES.keys()).index(st.session_state["selected_role"]),
            label_visibility="collapsed",
            key="role_radio",
        )
        st.session_state["selected_role"] = role

        if role == "HR":
            st.success("🔓 Full access — all categories visible")
        else:
            cats = ROLES.get(role, [])
            st.caption(f"Accessible categories: {', '.join(cats or [])}")

        st.divider()

        # Index status
        index, chunks = get_or_build_index()
        if index is not None:
            st.success(f"✅ Index ready — **{index.ntotal}** vectors")
            st.caption(f"From **{len(set(r['source'] for r in chunks))}** document(s)")
        else:
            st.warning("⚠️ No documents indexed.\nUpload files in the Admin Panel.")

        st.divider()

        # Quick stats
        if st.session_state["chat_history"]:
            total_q = sum(1 for m in st.session_state["chat_history"] if m["role"] == "user")
            helpful = sum(1 for f in st.session_state["feedback_log"] if f.get("helpful"))
            st.markdown(f"**📊 Session Stats**")
            st.caption(f"Questions asked: **{total_q}**")
            st.caption(f"Helpful responses: **{helpful}**")
            if st.button("🗑️ Clear Chat", key="clear_chat"):
                st.session_state["chat_history"] = []
                st.rerun()


render_sidebar()


# ── Determine Page ─────────────────────────────────────────────────────────

role = st.session_state["selected_role"]
is_admin = role == "HR"


# ── Admin Tab (HR only) ────────────────────────────────────────────────────

main_tab, admin_tab = st.tabs(["💬 Ask HR", "🔧 Admin Panel"]) if is_admin else (st.container(), None)


# ── Chat Interface ─────────────────────────────────────────────────────────

with main_tab:
    st.markdown('<p class="logo-title" style="font-size:1.4rem;">💬 Ask an HR Policy Question</p>', unsafe_allow_html=True)
    st.caption(
        "Answers are strictly grounded in your company's uploaded policy documents. "
        "No hallucination — if the policy doesn't say it, neither will I."
    )
    st.divider()

    # Chat history display
    chat_container = st.container()
    with chat_container:
        for i, message in enumerate(st.session_state["chat_history"]):
            if message["role"] == "user":
                st.markdown(f'<div class="chat-user">🙋 {message["content"]}</div>', unsafe_allow_html=True)
            else:
                with st.container():
                        # Enhanced Answer + Source + Confidence display
                    if message.get("sources"):
                        # Answer section
                        st.markdown(f'<div class="chat-bot">🤖 {message["content"]}</div>', unsafe_allow_html=True)
                        
                        # Source badges with better formatting
                        badge_html = ""
                        seen = set()
                        for src in message["sources"]:
                            label = f"{src['source']} · p{src['page']}"
                            if label not in seen:
                                badge_html += f'<span class="source-badge">📄 {label}</span>'
                                seen.add(label)
                        if badge_html:
                            st.markdown(badge_html, unsafe_allow_html=True)
                        
                        # Enhanced confidence display
                        if message.get("confidence") is not None:
                            conf = message["confidence"]
                            bar_color = "#4caf50" if conf >= 0.6 else ("#ff9800" if conf >= CONFIDENCE_THRESHOLD else "#f44336")
                            conf_label = "High" if conf >= 0.6 else ("Medium" if conf >= CONFIDENCE_THRESHOLD else "Low")
                            
                            st.markdown(
                                f'<div class="confidence-wrap">'
                                f'<div class="confidence-label">Confidence: {conf_label} ({conf:.0%})</div>'
                                f'<div style="background:rgba(255,255,255,0.1);border-radius:6px;height:8px;">'
                                f'<div style="width:{int(conf*100)}%;background:{bar_color};border-radius:6px;height:8px;transition:width 0.6s;"></div>'
                                f'</div></div>',
                                unsafe_allow_html=True,
                            )
                    else:
                        # Standard display for messages without sources
                        st.markdown(f'<div class="chat-bot">🤖 {message["content"]}</div>', unsafe_allow_html=True)

                    # Feedback buttons
                    col_a, col_b, col_c = st.columns([1, 1, 8])
                    if col_a.button("👍", key=f"like_{i}", help="Helpful"):
                        st.session_state["feedback_log"].append(
                            {"question": st.session_state["chat_history"][i - 1]["content"], "helpful": True}
                        )
                        st.toast("Thanks for the feedback! 🎉")
                    if col_b.button("👎", key=f"dislike_{i}", help="Not helpful"):
                        st.session_state["feedback_log"].append(
                            {"question": st.session_state["chat_history"][i - 1]["content"], "helpful": False}
                        )
                        st.toast("Thanks — we'll work on improving! 🙏")

    st.divider()

    # ── Query Input ───────────────────────────────────────────────────────
    with st.form("query_form", clear_on_submit=True):
        col_input, col_btn = st.columns([6, 1])
        user_query = col_input.text_input(
            "Ask a question…",
            placeholder="e.g. What is the sick leave policy?",
            label_visibility="collapsed",
            key="query_input",
        )
        submitted = col_btn.form_submit_button("Ask ➤", type="primary")

    # ── Process Query ─────────────────────────────────────────────────────
    if submitted and user_query.strip():
        query = user_query.strip()

        # Record user message
        st.session_state["chat_history"].append({"role": "user", "content": query})

        with st.spinner("🔍 Searching policy documents…"):
            index, chunk_records = get_or_build_index()

        if index is None or not chunk_records:
            answer = "⚠️ No policy documents have been indexed yet. Please ask your HR administrator to upload documents."
            bot_message = {"role": "assistant", "content": answer, "sources": [], "confidence": None}
        else:
            results = hybrid_search(query, index, chunk_records, role=role)

            if not is_answer_found(results):
                answer = "❌ This information is not available in the company policy documents."
                bot_message = {"role": "assistant", "content": answer, "sources": [], "confidence": results[0]["confidence"] if results else 0.0}
            else:
                context = format_context(results)
                with st.spinner("✍️ Generating answer…"):
                    answer = generate_answer(query, results, context)
                top_confidence = results[0]["confidence"] if results else 0.0
                bot_message = {
                    "role": "assistant",
                    "content": answer,
                    "sources": results,
                    "confidence": top_confidence,
                }

        st.session_state["chat_history"].append(bot_message)
        st.rerun()


# ── Admin Panel Tab ─────────────────────────────────────────────────────────

if is_admin and admin_tab is not None:
    with admin_tab:
        render_admin_panel()
