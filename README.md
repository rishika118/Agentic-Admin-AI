# Agentic AI for Administrative Support

> An intelligent administrative assistant that answers questions from official documents,
> generates reports, drafts letters, and compares policies — powered by Local LLMs via Ollama.

---

## 🗺️ Project Roadmap

| Phase | What We Build | Status |
|-------|---------------|--------|
| **1** | Project structure, FastAPI skeleton, React skeleton | ✅ Complete |
| **2** | PostgreSQL schema + SQLAlchemy ORM | ⏳ Next |
| **3** | PDF ingestion pipeline (parse → OCR → chunk → embed) | ⬜ |
| **4** | Qdrant vector store + retrieval | ⬜ |
| **5** | LangGraph agents (Planner, Retrieval, Task, Citation) | ⬜ |
| **6** | FastAPI endpoints (upload, chat, report, draft) | ⬜ |
| **7** | React frontend (full UI) | ⬜ |

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12 + FastAPI |
| Frontend | React 18 + Vite |
| LLM | Ollama → `mistral:latest` |
| Agents | LangGraph + LangChain |
| Vector DB | Qdrant |
| Relational DB | PostgreSQL |
| Embeddings | `BAAI/bge-small-en-v1.5` |
| PDF Parsing | PyMuPDF |
| OCR | PaddleOCR |

---

## 📁 Project Structure

```
Agentic-Admin-AI/
├── backend/
│   ├── app.py              ← FastAPI entry point
│   ├── config.py           ← All config (reads .env)
│   ├── requirements.txt    ← Python dependencies
│   ├── .env.example        ← Copy to .env and fill in values
│   │
│   ├── agents/             ← LangGraph agent definitions
│   │   ├── planner.py      ← Decides which agent to call
│   │   ├── retrieval.py    ← Searches Qdrant for relevant chunks
│   │   ├── task.py         ← Reports, drafts, comparisons
│   │   └── citation.py     ← Attaches source citations
│   │
│   ├── ingestion/          ← PDF processing pipeline
│   │   ├── parser.py       ← Extract text with PyMuPDF
│   │   ├── ocr.py          ← OCR with PaddleOCR (scanned PDFs)
│   │   ├── metadata.py     ← Extract title, date, dept, etc.
│   │   ├── chunking.py     ← Split text into chunks
│   │   └── embeddings.py   ← Generate vectors
│   │
│   ├── rag/                ← Retrieval-Augmented Generation
│   │   ├── retriever.py    ← Semantic search logic
│   │   └── vector_store.py ← Qdrant CRUD wrapper
│   │
│   ├── tools/              ← Task Agent tools
│   │   ├── report_tool.py
│   │   ├── drafting_tool.py
│   │   └── comparison_tool.py
│   │
│   ├── database/
│   │   └── postgres.py     ← SQLAlchemy engine + ORM models
│   │
│   ├── models/             ← Pydantic request/response schemas
│   ├── prompts/            ← LLM prompt strings
│   └── templates/          ← Letter/report text templates
│
├── frontend/
│   ├── index.html
│   ├── vite.config.js
│   ├── package.json
│   └── src/
│       ├── main.jsx        ← React bootstrap
│       ├── App.jsx         ← Routing + Navbar
│       ├── index.css       ← Global styles
│       └── pages/
│           ├── Dashboard.jsx
│           ├── Upload.jsx
│           ├── Assistant.jsx
│           ├── Report.jsx
│           └── DraftLetter.jsx
│
├── storage/
│   ├── uploads/            ← Uploaded PDFs saved here
│   └── pdfs/               ← Source PDFs from NIT Calicut website
│
├── docs/                   ← Architecture diagrams, notes
├── .gitignore
└── README.md
```

---

## ⚙️ Prerequisites

Install these **before** running the project:

1. **Python 3.12** — [python.org](https://www.python.org/downloads/)
2. **Node.js 18+** — [nodejs.org](https://nodejs.org/)
3. **PostgreSQL 15+** — [postgresql.org](https://www.postgresql.org/download/)
4. **Qdrant** — Download binary from [qdrant.tech](https://qdrant.tech/documentation/quick-start/)
5. **Ollama** — [ollama.com](https://ollama.com/)

---

## 🚀 Setup Instructions

### Step 1 — Clone the repository

```bash
git clone <your-repo-url>
cd Agentic-Admin-AI
```

---

### Step 2 — Set up the Backend

```bash
# Navigate to the backend folder
cd backend

# Create a Python virtual environment
python -m venv venv

# Activate the virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install all Python dependencies
pip install -r requirements.txt

# Copy the environment file
cp .env.example .env

# Edit .env and fill in your PostgreSQL password and other values
# (Use Notepad, VS Code, or any text editor)
```

---

### Step 3 — Set up the Frontend

```bash
# Navigate to the frontend folder (from project root)
cd frontend

# Install Node.js dependencies
npm install
```

---

### Step 4 — Start External Services

**Start Qdrant** (in a separate terminal):
```bash
# Navigate to where you downloaded Qdrant
./qdrant
# Qdrant runs on http://localhost:6333
```

**Start Ollama and pull the model** (in a separate terminal):
```bash
# Start Ollama
ollama serve

# In another terminal, pull the Mistral model
ollama pull mistral
```

**Make sure PostgreSQL is running** and you've created the database:
```sql
-- In psql or pgAdmin:
CREATE DATABASE agentic_admin;
```

---

### Step 5 — Run the Backend

```bash
# From the backend/ folder with venv activated
cd backend
uvicorn app:app --reload --port 8000
```

Visit: **http://localhost:8000/docs** — you should see the Swagger UI.

---

### Step 6 — Run the Frontend

```bash
# From the frontend/ folder
cd frontend
npm run dev
```

Visit: **http://localhost:5173** — you should see the dashboard.

---

## 🧪 How to Test Phase 1

After running both servers:

1. Open **http://localhost:8000/health** — should return:
   ```json
   {"status": "ok", "app": "Agentic Admin AI", "version": "1.0.0", "environment": "development"}
   ```

2. Open **http://localhost:8000/docs** — should show the Swagger API documentation.

3. Open **http://localhost:5173** — should show the dark-mode dashboard with navbar.

4. Click through all navbar links: Dashboard, Upload, AI Assistant, Reports, Draft Letter.

---

## 📖 Understanding the Code

Each Python file starts with a **docstring** explaining:
- What the file does
- Why it exists  
- How it connects to the rest of the project

Read these comments as you explore the code — they're written for beginners.

---

## 👨‍💻 Author

Summer Internship Project — NIT Calicut  
Built with ❤️ using FastAPI, React, LangGraph, and Ollama.
