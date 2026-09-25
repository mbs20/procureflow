# ADR 0001: Architecture and Core Technology Stack

## Status
Accepted

## Context
ProcureFlow OSS is designed as an open-source, quotation comparison and procurement decision-support engine. The system needs to ingest unstructured and semi-structured documents (PDFs, Excel, CSV), extract complex line items with high fidelity, normalize disparate metrics (currencies, units, delivery terms), and evaluate bids using a transparent, configurable scoring engine.

We evaluated potential technology stacks:
1. **Full-stack TypeScript / Next.js**: While strong for web UI, Python offers established libraries for document parsing (PyMuPDF, pdfplumber, openpyxl, pandas), OCR, tabular data handling, and structured provider output.
2. **Python Django / Django REST Framework**: Comprehensive but monolithic, heavier runtime overhead, and less native support for modern asynchronous I/O and Pydantic validation than FastAPI.
3. **Decoupled FastAPI (Python) + React (TypeScript)**: Combines Python's strengths in document processing with a modern, reactive TypeScript dashboard.

## Decision
We select:
- **Backend**: Python 3.12+ with FastAPI, SQLAlchemy 2.0 (asyncio), Alembic, Pydantic v2, and Celery with Redis for background task execution.
- **Frontend**: React 18+ with Vite, TypeScript, TanStack Query, TanStack Table, and Tailwind CSS + Radix/shadcn UI primitives.
- **Database**: PostgreSQL 16 as the primary relational store (supporting JSONB for raw extractions and snapshot storage).
- **Architecture**: A modular monolith with strictly isolated service domains (extraction, normalization, scoring, RFQs, audit and narratives).

## Consequences
- **Positive**: Clean separation of concerns; backend auto-generates type-safe OpenAPI schemas; easy for external contributors to extend parsers or scoring algorithms without touching UI code; easily containerized with Docker Compose.
- **Negative**: Requires maintaining two separate language runtimes (Python and TypeScript) in the repository. Docker Compose and contract tests help manage the two runtimes; frontend API clients are currently handwritten.
