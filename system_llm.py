"""
system_llm.py - Ollama-based LLM answer generation for HRCompassAI
All answers are generated using a lighter Ollama model for CPU-friendly, policy-grounded responses.
"""
from __future__ import annotations
import re
from typing import List, Dict, Any
from config import (
    OPENAI_API_KEY,
    OPENAI_MODEL,
    OLLAMA_MODEL,
    OLLAMA_TEMPERATURE,
    OLLAMA_TIMEOUT,
    OLLAMA_RETRIES,
)
from utils import build_strict_prompt


def _post_process_answer(answer: str) -> str:
    """Clean and format the generated answer for readability."""
    if not answer:
        return ""

    answer = answer.replace('\r\n', '\n').replace('\r', '\n')
    answer = re.sub(r'\n{3,}', '\n\n', answer)
    answer = re.sub(r'[ \t]+', ' ', answer)
    answer = re.sub(r' *\n *', '\n', answer).strip()
    answer = re.sub(r'^(Answer:\s*)', '', answer, flags=re.IGNORECASE)
    answer = re.sub(r'\.([A-Z])', r'. \1', answer)
    return answer


def answer_with_ollama(context: str, question: str) -> str:
    """Generate answer using Ollama with CPU-friendly model and retries."""
    import requests

    url = "http://localhost:11434/api/generate"
    prompt = build_strict_prompt(context, question)
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": OLLAMA_TEMPERATURE,
            "num_predict": 300,
        },
    }

    for attempt in range(1, OLLAMA_RETRIES + 1):
        try:
            response = requests.post(url, json=payload, timeout=OLLAMA_TIMEOUT)
            response.raise_for_status()
            data = response.json()
            answer = (data.get("response") or "").strip()
            return _post_process_answer(answer)
        except requests.exceptions.ConnectionError:
            if attempt == OLLAMA_RETRIES:
                return "Error: Ollama is not reachable. Please start Ollama or check the server."
        except requests.exceptions.Timeout:
            if attempt == OLLAMA_RETRIES:
                return "Error: Ollama request timed out"
        except requests.exceptions.HTTPError as exc:
            if attempt == OLLAMA_RETRIES:
                status = exc.response.status_code if exc.response is not None else "unknown"
                return f"Error: Ollama HTTP {status}"
        except Exception as exc:
            if attempt == OLLAMA_RETRIES:
                return f"Error: {str(exc)}"

    return "Error: Ollama request failed"


def answer_with_openai(context: str, question: str) -> str:
    """Generate answer using OpenAI API as fallback."""
    if not OPENAI_API_KEY:
        return answer_with_ollama(context, question)

    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        prompt = build_strict_prompt(context, question)
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "user", "content": prompt},
            ],
            temperature=OLLAMA_TEMPERATURE,
            max_tokens=500,
        )
        answer = response.choices[0].message.content or ""
        return _post_process_answer(answer)
    except Exception as exc:
        return f"Error: {str(exc)}"


def generate_answer(question: str, results: List[Dict[str, Any]], context: str) -> str:
    """Generate answer using Ollama for natural, human-like responses."""
    if not context:
        return "Not available in policy"

    return answer_with_ollama(context, question)
