# ADR 0003: Asynchronous Task Processing with Celery and Redis

## Status
Accepted

## Context
Document ingestion tasks—such as parsing multi-page vector PDFs, OCRing scanned documents, executing LLM extraction calls, and running normalization—are I/O and CPU intensive. Running these synchronously in HTTP request handlers would cause web server timeouts, tie up worker threads, and degrade API responsiveness.

## Decision
We decouple web serving from ingestion jobs using **Celery** with **Redis** as both broker and result store.
- File uploads immediately stream to storage and respond with a unique Quotation ID in `queued` status.
- Celery workers process the document asynchronously through the ingestion pipeline.
- The status of each document is trackable via `GET /api/v1/quotations/{id}/job-status`.
- In unit testing and local lightweight development without Redis, Celery supports `CELERY_ALWAYS_EAGER=true` for synchronous in-process execution.

## Consequences
- **Positive**: Web API remains fast and resilient; jobs can be retried automatically with backoff; supports worker autoscaling under high sourcing volumes.
- **Negative**: Adds operational requirement for Redis and a dedicated worker process in production environments.
