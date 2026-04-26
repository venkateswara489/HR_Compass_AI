# HRCompassAI - Employee Policy Retrieval Assistant

RAG assistant for HR policies using:
- Python (Flask backend)
- React (Frontend)
- FAISS
- Sentence Transformers
- Ollama (`llama3` or `mistral`)

## Project Structure

```
HRCompassAI/
├── app.py                 # Flask backend API
├── embeddings.py          # Document embedding generation
├── retriever.py           # FAISS retrieval logic
├── system_llm.py          # Ollama-based answer generation
├── utils.py               # Shared utility functions
├── config.py              # Configuration settings
├── requirements.txt       # Python dependencies
├── documents/             # Uploaded HR policy files
├── vector_store/          # FAISS index and metadata
└── frontend/              # React frontend
    ├── package.json
    ├── src/
    └── node_modules/
```

## Features

- Multi-document upload (`.pdf`, `.docx`, `.txt`)
- Chunking with overlap (`chunk_size` 300-500, overlap 50 by default)
- Embedding model: `all-MiniLM-L6-v2`
- FAISS retrieval (`top_k=3`) with similarity threshold filtering
- Ollama grounded answer generation (temperature `0.0`)
- Strict no-hallucination prompt
- "Not available in policy" fallback
- Chat history via Streamlit session state
- Output format:
  - Answer
  - Source
  - Confidence

## Run Instructions

### 1) Install dependencies

**Backend (Python):**
```bash
pip install -r requirements.txt
```

**Frontend (Node.js):**
```bash
cd frontend
npm install
```

### 2) Install and Setup Ollama

Install Ollama from https://ollama.com, then pull the model:

```bash
ollama pull llama3
# or
ollama pull mistral
```

### 3) Start Ollama Service

**IMPORTANT: Ollama must be running before starting the app.**

```bash
ollama serve
```

This starts the Ollama server on `http://localhost:11434`. Keep this terminal open.

### 4) Start Flask Backend

In a new terminal, run:

```bash
python app.py
```

This starts the Flask API on `http://localhost:5000`. Keep this terminal open.

### 5) Start React Frontend

In another new terminal, run:

```bash
cd frontend
npm run dev
```

This starts the React frontend (usually on `http://localhost:5173`).

### 6) Use the app

1. Open your browser to the frontend URL (e.g., `http://localhost:5173`)
2. Upload HR policy files in the admin panel.
3. Click **Build / Refresh Index**.
4. Ask policy questions in the query box.


**Note:** The FAISS index is saved in `vector_store/`, so you don't need to rebuild it after restarting the app unless you upload new documents.
