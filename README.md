# 🤖 Agentic AI for Administrative Support

An AI-powered administrative assistant developed as part of my **Summer Internship at NIT Calicut**.

The project aims to simplify administrative workflows by combining **Retrieval-Augmented Generation (RAG)** with **Agentic AI**. Instead of functioning as a traditional chatbot, the system is designed to understand institutional documents, reason over them, and assist with administrative tasks such as answering queries, generating reports, drafting official letters, and comparing policies.

> **Current Status:** MVP under active development.

---

## ✨ Features

### Current MVP
- FastAPI backend
- React + Vite frontend
- PostgreSQL integration
- Modular project architecture
- Local LLM support using Ollama
- API documentation with Swagger
- Foundation for document upload and retrieval

### Planned Features
- PDF ingestion pipeline
- Automatic OCR for scanned documents
- Metadata extraction
- Semantic search using Qdrant
- Multi-agent workflow using LangGraph
- Report generation
- Letter and request drafting
- Policy comparison
- Source citation and document redirection
- Role-based access control
- Support for Email, Excel, Word, APIs, Google Drive, and SharePoint

---

# 🏗️ System Architecture

```
                 +----------------------+
                 |    React Frontend    |
                 +----------+-----------+
                            |
                            |
                    FastAPI REST API
                            |
        +-------------------+-------------------+
        |                   |                   |
        |                   |                   |
  PostgreSQL           LangGraph Agents      Qdrant
 (Metadata)           (Planning & Tasks)   (Vector DB)
        |                   |                   |
        +-------------------+-------------------+
                            |
                      Ollama (Mistral)
                            |
                   Retrieved Administrative
                          Documents
```

---

# 🛠 Tech Stack

| Category | Technology |
|----------|------------|
| Backend | FastAPI |
| Frontend | React + Vite |
| Language | Python 3.12 |
| Database | PostgreSQL |
| Vector Database | Qdrant |
| LLM | Ollama (Mistral) |
| Agent Framework | LangGraph |
| Embeddings | BAAI/bge-small-en-v1.5 |
| PDF Parsing | PyMuPDF |
| OCR | PaddleOCR *(planned)* |

---

# 📂 Project Structure

```
Agentic-Admin-AI
│
├── backend/
│   ├── agents/
│   ├── ingestion/
│   ├── rag/
│   ├── routers/
│   ├── database/
│   ├── models/
│   ├── tools/
│   ├── templates/
│   ├── prompts/
│   ├── app.py
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   ├── public/
│   └── package.json
│
├── storage/
│   ├── pdfs/
│   └── uploads/
│
├── docs/
└── README.md
```

---

# 🚀 Getting Started

## Clone the repository

```bash
git clone https://github.com/rishika118/Agentic-Admin-AI.git
cd Agentic-Admin-AI
```

---

## Backend

```bash
cd backend

python -m venv venv

# Windows
venv\Scripts\activate

# Linux / macOS
source venv/bin/activate

pip install -r requirements.txt
```

Create a `.env` file from `.env.example` and configure your PostgreSQL credentials.

Run the backend:

```bash
uvicorn app:app --reload
```

Swagger documentation:

```
http://localhost:8000/docs
```

---

## Frontend

```bash
cd frontend

npm install

npm run dev
```

Open:

```
http://localhost:5173
```

---


# 🎯 Future Scope

The architecture has been designed to support additional enterprise data sources, including:

- Internal administrative documents
- Emails
- Excel spreadsheets
- Word documents
- Databases
- REST APIs
- Google Drive
- Microsoft SharePoint

without requiring significant architectural changes.

---




## ⭐ Acknowledgements

This project is being developed as part of the **NIT Calicut Summer Internship Program** and serves as an MVP for a scalable Agentic AI platform for administrative support.