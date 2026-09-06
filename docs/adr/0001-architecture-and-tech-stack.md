# ADR 0001: Architecture and Core Technology Stack

## Status
Accepted

## Context
ProcureFlow OSS is designed as an open-source, AI-assisted procurement decision and quotation comparison engine. The system needs to ingest unstructured and semi-structured documents (PDFs, Excel, CSV), extract complex line items with high fidelity, normalize disparate metrics (currencies, units, delivery terms), and evaluate bids using a transparent, configurable scoring engine.

We evaluated potential technology stacks:
1. **Full-stack TypeScript / Next.js**: While strong for web UI, the Python ecosystem is overwhelmingly superior for document parsing (PyMuPDF, pdfplumber, openpyxl, pandas), OCR, tabular data handling, and AI structured output libraries.
2. **Python Django / Django REST Framework**: Comprehensive but monolithic, heavier runtime overhead, and less native support for modern asynchronous I/O and Pydantic validation than FastAPI.
3. **Decoupled FastAPI (Python) + React (TypeScript)**: Combines Python's strengths in document/AI processing with a modern, reactive TypeScript dashboard.

## Decision
We select:
- **Backend**: Python 3.12+ with FastAPI, SQLAlchemy 2.0 (asyncio), Alembic, Pydantic v2, and Celery with Redis for background task execution.
- **Frontend**: React 18+ with Vite, TypeScript, TanStack Query, TanStack Table, and Tailwind CSS + Radix/shadcn UI primitives.
- **Database**: PostgreSQL 16 as the primary relational store (supporting JSONB for raw extractions and snapshot storage).
- **Architecture**: A modular monolith with strictly isolated service domains (`ingestion`, `scoring`, `rfq`, `audit`, `ai`).

## Consequences
- **Positive**: Clean separation of concerns; backend auto-generates type-safe OpenAPI schemas; easy for external contributors to extend parsers or scoring algorithms without touching UI code; easily containerized with Docker Compose.
- **Negative**: Requires maintaining two separate language runtimes (Python and TypeScript) in the repository. Mitigated through Docker Compose and automated OpenAPI client generation.
