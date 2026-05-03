"""
config.py
Centralized configuration for HRCompassAI.
All paths, model settings, and tunable parameters live here.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Directories ──────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
DOCUMENTS_DIR = BASE_DIR / "data" / "documents"
VECTOR_STORE_DIR = BASE_DIR / "data" / "vector_store"

DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)

# ── Embedding Model ────────────────────────────────────────────────────────
# Free local model — no API key required
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384  # must match the model output size

# ── Chunking ───────────────────────────────────────────────────────────────
CHUNK_SIZE = 300       # characters per chunk - smaller for precision
CHUNK_OVERLAP = 50     # overlap between consecutive chunks

# ── FAISS Retrieval ────────────────────────────────────────────────────────
TOP_K = 5                          # number of chunks returned per query - increased for better coverage
CONFIDENCE_THRESHOLD = 0.25        # below this → "not found in policy" - lowered to catch more matches
DISTANCE_THRESHOLD = 2.0          # maximum L2 distance for acceptable matches - increased to allow more distant matches

# ── LLM ───────────────────────────────────────────────────────────────────
# Set OPENAI_API_KEY in a .env file; leave blank to use the stub response.
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = "gpt-3.5-turbo"

# Ollama model settings for local CPU usage
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "phi3")
OLLAMA_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0.2"))
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "120"))
OLLAMA_RETRIES = int(os.getenv("OLLAMA_RETRIES", "2"))

# ── Role-Based Access ──────────────────────────────────────────────────────
ROLES = {
    "Employee": ["General", "Leave", "Code of Conduct", "Benefits"],
    "HR":       None,   # None means unrestricted — sees everything
}

# ── FAISS Index Files ──────────────────────────────────────────────────────
FAISS_INDEX_PATH   = VECTOR_STORE_DIR / "hr_faiss.index"
METADATA_STORE_PATH = VECTOR_STORE_DIR / "hr_metadata.json"
