"""
system_llm.py - Simple, focused LLM answer generation
"""
from __future__ import annotations
import re
from typing import List, Dict, Any
from config import OPENAI_API_KEY, OPENAI_MODEL, CONFIDENCE_THRESHOLD


_SYSTEM_PROMPT = """You are HRCompassAI, an HR Policy Assistant.
Answer questions ONLY using the provided context.
RULES:
1. Give 1-2 sentences maximum. VERY SHORT.
2. Answer directly without extra info.
3. If not in context, say: "This information is not available in the company policy documents."
"""

_USER_TEMPLATE = """Context: {context}

Question: {question}

Answer in 1-2 sentences only."""


def truncate_to_sentences(text: str, num_sentences: int = 2) -> str:
    """Extract first N sentences from text."""
    if not text:
        return ""
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    result = " ".join(sentences[:num_sentences])
    return result.strip()


def _clean_context_text(text: str) -> str:
    """Remove headers/noise and normalize whitespace."""
    cleaned = re.sub(r"\[Source:[^\]]+\]", " ", text or "", flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _pick_best_sentence(question: str, text: str) -> str:
    """Pick the most relevant complete sentence from retrieved text."""
    cleaned = _clean_context_text(text)
    if not cleaned:
        return ""

    # Prefer complete sentence boundaries.
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", cleaned) if s.strip()]
    if not sentences:
        return ""

    # Drop likely leading fragment from chunk boundary.
    if len(sentences) > 1 and sentences[0] and sentences[0][0].islower():
        sentences = sentences[1:]

    q_terms = set(re.findall(r"[a-zA-Z]{4,}", question.lower()))
    if not q_terms:
        return sentences[0]

    def is_noise_sentence(s: str) -> bool:
        upper = s.upper()
        return (
            "====" in s
            or "COMPANY:" in upper
            or "DOCUMENT:" in upper
            or "VERSION:" in upper
            or "SECTION " in upper
        )

    filtered = [s for s in sentences if not is_noise_sentence(s)]
    if filtered:
        sentences = filtered

    query_lower = question.lower()
    phrase_terms = [f"{m[0]} {m[1]}" for m in zip(re.findall(r"[a-zA-Z]{3,}", query_lower), re.findall(r"[a-zA-Z]{3,}", query_lower)[1:])]
    wants_leave = "leave" in query_lower
    asks_quantity = ("how many" in query_lower) or ("days" in query_lower) or ("entitled" in query_lower)

    def score_sentence(s: str) -> tuple[int, int, int]:
        lower = s.lower()
        overlap = sum(1 for w in q_terms if w in lower)
        phrase_overlap = sum(1 for p in phrase_terms if p in lower)
        policy_boost = 0
        if wants_leave:
            if "entitled" in lower:
                policy_boost += 4
            if "days" in lower:
                policy_boost += 2
            if "leave" in lower:
                policy_boost += 1
        if asks_quantity:
            if re.search(r"\b\d+\b", lower):
                policy_boost += 4
            if "per year" in lower or "calendar year" in lower:
                policy_boost += 2
            if "applied" in lower or "advance" in lower:
                policy_boost -= 1
        # Prefer medium-length human-readable sentences.
        length_penalty = abs(len(s) - 130)
        return (overlap + (phrase_overlap * 3) + policy_boost, -length_penalty, -len(s))

    ranked = sorted(
        sentences,
        key=score_sentence,
        reverse=True,
    )
    return ranked[0] if ranked else sentences[0]


def _extract_topic_sentence(question: str, text: str) -> str:
    """Extract sentence around the closest topic phrase from the question."""
    cleaned = _clean_context_text(text)
    if not cleaned:
        return ""

    q_words = re.findall(r"[a-zA-Z]{3,}", question.lower())
    if not q_words:
        return ""

    phrases = [f"{q_words[i]} {q_words[i+1]}" for i in range(len(q_words) - 1)]
    phrases.extend(q_words)
    low = cleaned.lower()

    for phrase in phrases:
        idx = low.find(phrase)
        if idx == -1:
            continue

        # Get a small window around the matched topic phrase.
        start = max(0, idx - 120)
        end = min(len(cleaned), idx + 260)
        window = cleaned[start:end]

        # Clip to sentence boundaries when possible.
        dot_before = window.find(". ")
        if dot_before != -1 and start > 0:
            window = window[dot_before + 2 :]
        dot_after = window.find(". ")
        if dot_after != -1:
            window = window[: dot_after + 1]

        candidate = window.strip()
        if candidate:
            return candidate

    return ""


def answer_with_openai(context: str, question: str) -> str:
    """Call OpenAI API for answer."""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": _USER_TEMPLATE.format(
                    context=context, question=question
                )},
            ],
            temperature=0.2,
            max_tokens=80,
        )
        answer = response.choices[0].message.content or ""
        return truncate_to_sentences(answer, 2)
    except Exception as e:
        return f"Error: {str(e)}"


def answer_without_key(context: str, question: str) -> str:
    """Fallback: extract answer from context without API key."""
    if not context or not question:
        return "This information is not available in the company policy documents."

    lower_q = question.lower()
    cleaned = _clean_context_text(context)

    # Target common leave entitlement questions with direct pattern extraction.
    if "annual leave" in lower_q and ("how many" in lower_q or "days" in lower_q):
        m = re.search(r"(annual leave[^.]*entitled to\s+\d+\s+days[^.]*)\.", cleaned, flags=re.IGNORECASE)
        if m:
            return truncate_to_sentences(m.group(1).strip() + ".", 1)
    if "sick leave" in lower_q:
        m = re.search(r"(sick leave[^.]*entitled to\s+\d+\s+days[^.]*)\.", cleaned, flags=re.IGNORECASE)
        if m:
            return truncate_to_sentences(m.group(1).strip() + ".", 1)

    best = _pick_best_sentence(question, context)
    if not best:
        return "This information is not available in the company policy documents."

    # Keep output short and easy to read.
    return truncate_to_sentences(best, 1)


def generate_answer(question: str, results: List[Dict[str, Any]], context: str) -> str:
    """Generate answer from retrieved context."""
    if not context:
        return "This information is not available in the company policy documents."
    
    # Use multiple top hits in fallback path to avoid bad chunk boundaries.
    fallback_text = " ".join((r.get("text", "") or "") for r in (results[:3] if results else []))

    if OPENAI_API_KEY:
        return answer_with_openai(context, question)
    else:
        return answer_without_key(fallback_text or context, question)
