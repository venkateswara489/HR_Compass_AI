"""Shared utility functions for HRCompassAI."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple
import re

import requests


def ensure_dirs(*paths: Path) -> None:
    """Create directories if missing."""
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)


def clean_text(text: str) -> str:
    """Normalize whitespace and remove empty noise."""
    if not text:
        return ""
    text = text.replace("\x00", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def build_context(retrieved: List[Dict], max_chars: int = 1200) -> str:
    """Build concise LLM context from top retrieved chunks."""
    blocks: List[str] = []
    total = 0
    for item in retrieved:
        block = f"[Source: {item['source']} | Page: {item['page']}]\n{item['text']}"
        if total + len(block) > max_chars:
            break
        blocks.append(block)
        total += len(block)
    return "\n\n".join(blocks)


def build_strict_prompt(context: str, question: str) -> str:
    """Construct a strict prompt for policy-grounded HR answers."""
    return (
        "You are HRCompassAI, an HR policy assistant.\n\n"
        "Your task is to answer questions ONLY using the provided context.\n\n"
        "RULES:\n"
        "- Do NOT add assumptions or suggestions\n"
        "- Do NOT give advice like 'I recommend'\n"
        "- Do NOT use outside knowledge\n"
        "- Answer only from the given policy content\n"
        "- If answer is not clearly present, say: 'Not available in policy'\n"
        "- Keep answers clear and complete (not too short, not too long)\n\n"
        f"Context:\n{context}\n\n"
        "Question:\n"
        f"{question}\n\n"
        "Answer:"
    )


def ask_ollama(
    prompt: str,
    model: str = "llama3",
    temperature: float = 0.7,  # Higher for more natural, varied responses
    timeout: int = 60,
) -> str:
    """Call local Ollama generate endpoint with longer response allowance."""
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature, "num_predict": 500},  # Allow complete answers
    }
    res = requests.post(url, json=payload, timeout=timeout)
    res.raise_for_status()
    data = res.json()
    return (data.get("response") or "").strip()


def format_answer_output(answer: str, source_names: List[str], confidence: float) -> str:
    """Render response in required output format with proper formatting."""
    source_text = ", ".join(source_names) if source_names else "N/A"
    conf_percent = f"{int(confidence * 100)}%"
    return (
        f"Answer:\n{answer}\n\n"
        f"Source:\n{source_text}\n\n"
        f"Confidence:\n{conf_percent}"
    )


def extract_unique_sources(retrieved: List[Dict]) -> List[Tuple[str, int]]:
    """Return unique (source, page) tuples preserving order."""
    seen = set()
    rows: List[Tuple[str, int]] = []
    for item in retrieved:
        key = (item["source"], int(item["page"]))
        if key in seen:
            continue
        seen.add(key)
        rows.append(key)
    return rows
