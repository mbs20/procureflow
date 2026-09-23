# ADR 0003: Asynchronous Task Processing with Celery and Redis

## Status
Accepted

## Context
Document ingestion tasks—such as parsing multi-page vector PDFs, OCRing scanned documents, executing LLM extraction calls, and running normalization—are I/O and CPU intensive. Running these synchronously in HTTP request handlers would cause web server timeouts, tie up worker threads, and degrade API responsiveness.

## Decision
We decouple web serving from ingestion jobs using **Celery** with **Redis** as both broker and result store.
- File uploads are saved to storage and respond with a unique Quotation ID in `uploaded` status.
- `POST /api/v1/quotations/{id}/extract` queues or retries extraction; Celery workers process the document asynchronously.
- Read quotation status via `GET /api/v1/quotations/{id}` and the latest result via `GET /api/v1/quotations/{id}/extractions/latest`.
- In unit testing and local lightweight development without Redis, Celery supports `CELERY_ALWAYS_EAGER=true` for synchronous in-process execution.

## Consequences
- **Positive**: Web API remains fast and resilient; jobs can be retried automatically with backoff; supports worker autoscaling under high sourcing volumes.
- **Negative**: Adds operational requirement for Redis and a dedicated worker process in production environments.
