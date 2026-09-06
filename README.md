# ProcureFlow OSS

<div align="center">

**Open-source AI-assisted RFQ comparison and procurement decision engine.**

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/Python-3.12%2B-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18%2B-61DAFB?logo=react)](https://react.dev)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?logo=postgresql)](https://www.postgresql.org)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker)](https://www.docker.com)

</div>

---

## 🎯 What is ProcureFlow OSS?

Procurement teams and SMEs constantly receive vendor quotations across heterogeneous formats: PDFs, Excel sheets, CSVs, and scanned docs. Today, the de-facto workflow is an error-prone manual copy-paste into spreadsheets, zero auditability, subjective evaluations, and no explainable decision trail.

**ProcureFlow OSS** transforms messy supplier quotations into **structured, transparent, and explainable procurement decisions**.

### Why ProcureFlow is different:
- **Document-First & Multi-Format**: Ingests real-world supplier files directly (PDF, XLSX, CSV).
- **Deterministic & Offline-Capable**: Structured files parse deterministically without requiring an LLM API key.
- **Source Citation on Every Value**: Extracted prices, quantities, and terms link directly to the page and line in the source file.
- **Transparent Weighted Scoring**: Transparent linear scoring with explicit criteria weighting and knockout logic. No hidden black boxes.
- **Human-in-the-Loop Safeguards**: AI proposes, extracts, and summarizes; humans verify, approve, and authorize final decisions.
- **Immutable Audit Trail**: Append-only log of every extraction adjustment, scoring weight update, and award justification.

---

## 🏗️ Architecture Overview

```
                               ┌────────────────────────┐
                               │  React + TypeScript UI │
                               │  (Vite, shadcn, Radix) │
                               └───────────┬────────────┘
                                           │ REST / WebSocket
                               ┌───────────▼────────────┐
                               │     FastAPI Backend    │
                               │  (Pydantic, SQLAlchemy)│
                               └─────┬──────────────┬───┘
                                     │              │
                   ┌─────────────────▼───┐    ┌─────▼────────────────┐
                   │  PostgreSQL 16 DB   │    │  Celery Task Worker  │
                   │ (Snapshots, Audits) │    │  (Redis Queue)       │
                   └─────────────────────┘    └─────┬────────────────┘
                                                    │
                                      ┌─────────────▼──────────────┐
                                      │ Ingestion & Pipeline       │
                                      │ - PDF/Excel/CSV Parsers    │
                                      │ - Instructor LLM Engine    │
                                      │ - Normalisation Engine     │
                                      └────────────────────────────┘
```

---

## ⚡ Quick Start

### 1. Prerequisites
- [Docker](https://docs.docker.com/get-docker/) & Docker Compose **or**
- Python 3.12+ and Node.js 20+ for local installation.

### 2. Run with Docker Compose
```bash
# Clone the repository
git clone https://github.com/mbs20/procureflow.git
cd procureflow

# Configure environment
cp .env.example .env

# Launch services
docker compose up -d
```

Open your browser:
- **Web Dashboard**: [http://localhost:5173](http://localhost:5173)
- **FastAPI Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **API Health Check**: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

---

## 💻 Local Development (Without Docker)

### Backend Setup
```bash
cd backend
python -m uv venv
source .venv/bin/activate # On Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"

# Run database migrations
alembic upgrade head

# Start API server
uvicorn procureflow.main:app --reload --port 8000

# Start Celery worker (in a separate terminal)
celery -A procureflow.tasks.celery_app worker --loglevel=info
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

---

## 🧪 Testing

```bash
# Run backend test suite
cd backend
pytest -v --cov=procureflow tests/

# Run specific unit tests (no DB or external services required)
pytest tests/unit/
```

---

## 🤝 Contributing

We welcome contributions from the community! Please read our [CONTRIBUTING.md](CONTRIBUTING.md) guide and [Code of Conduct](CODE_OF_CONDUCT.md) before submitting pull requests.

Check out our [Architecture Decision Records (ADRs)](docs/adr/) to understand our technical design choices.

---

## 📄 License

ProcureFlow OSS is open-source software licensed under the [Apache License 2.0](LICENSE).
