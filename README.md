# HRCompassAI 🧭

> A Retrieval-Augmented Generation (RAG) system for HR — providing **accurate, policy-grounded answers** from internal company documents using FAISS vector search and sentence embeddings. Supports both a Streamlit UI and a React + Flask frontend.

---

## 🚀 Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. (Optional) Configure OpenAI API key
```bash
copy .env.example .env
# Edit .env and add your OPENAI_API_KEY
```
> The app can still answer questions without an API key using local extraction from retrieved policy text.

### 3. Run the Streamlit app
```bash
streamlit run app.py
```

### 4. Run the React frontend + Flask API
```bash
python api.py
cd frontend
npm install
npm run dev
```
> The React app communicates with the backend at `http://localhost:5000`.

---

## 🏗️ Project Structure

```
HRCompassAI/
├── app.py              # Streamlit UI + chat interface
├── api.py              # Flask REST API for the React frontend
├── config.py           # Central settings, paths, roles, and thresholds
├── embeddings.py       # Document loading, chunking, embedding generation
├── retriever.py        # FAISS index, BM25 search, role filtering, confidence scoring
├── system_llm.py       # LLM answer generation and fallback extraction
├── admin.py            # Admin document upload/delete/rebuild logic
├── requirements.txt    # Python dependencies
├── .env.example        # Example environment variables
├── data/
│   ├── documents/      # Upload your HR policy files here
│   └── vector_store/   # Auto-generated FAISS index files
└── frontend/           # React + Vite frontend
    ├── package.json
    └── src/
```

---

## 🔑 Key Features

| Feature | Description |
|---|---|
| 🔍 Hybrid Search | FAISS semantic search + BM25 keyword ranking |
| 📄 Source Attribution | Answers include source document and page metadata |
| 📊 Confidence Score | Visual confidence bar and label for each response |
| 🚫 Grounded Answers | Returns “not available” if the top result is below threshold |
| 👔 Role-Based Access | Employee / Manager / HR roles filter policy categories |
| 💬 Chat History | Session-level conversation memory in Streamlit UI |
| 👍👎 Feedback | Rate answers as helpful or not helpful |
| 🔧 Admin Controls | Upload/delete documents and rebuild index without restart |
| 💡 Optional LLM | Uses OpenAI when the key is set, otherwise local extraction |

---

## 📚 Architecture

```
User Question -> Retrieval -> Context Selection -> Answer Generation

UI: Streamlit app or React frontend
Backend: Flask API or Streamlit direct integration
Retriever: FAISS + BM25 + role filtering
LLM: OpenAI (optional) or local context extraction
```

---

## 📝 Notes

- `data/documents/` stores uploaded policy files.
- `data/vector_store/` contains `hr_faiss.index` and `hr_metadata.json`.
- The React frontend lives in `frontend/` and consumes `api.py`.
- If `OPENAI_API_KEY` is not provided, the app falls back to rule-based extraction from retrieved text.

---

## 🎓 Key Points (for Viva)

- *"This system uses FAISS for fast approximate nearest-neighbour similarity search."*
- *"We use sentence-transformers to capture semantic meaning beyond keywords."*
- *"Overlapping chunking (300 chars, 50 overlap) improves retrieval accuracy."*
- *"The LLM is strictly instructed to use only retrieved context — preventing hallucination."*
- *"Hybrid BM25 + FAISS search combines lexical and semantic matching."*
- *"Role-based access control ensures employees only see policies relevant to them."*
- *"This is a Retrieval-Augmented Generation (RAG) system."*
