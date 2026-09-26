.PHONY: help install test test-backend test-frontend lint format dev-backend dev-frontend

help:
	@echo "Requires uv, Node.js/npm, and GNU Make; explicit commands are in CONTRIBUTING.md."
	@echo "make install       Install locked backend and frontend dependencies"
	@echo "make test          Run backend and frontend unit/integration tests"
	@echo "make lint          Run Ruff lint/format checks, mypy, and TypeScript checks"
	@echo "make format        Format backend src and tests using Ruff"
	@echo "make dev-backend   Start API using backend/.env (see README)"
	@echo "make dev-frontend  Start Vite development server"

install:
	uv sync --directory backend --frozen --extra dev
	npm --prefix frontend ci

test: test-backend test-frontend

test-backend:
	uv run --directory backend --no-sync pytest tests/ -v --cov=procureflow

test-frontend:
	npm --prefix frontend test

lint:
	uv run --directory backend --no-sync ruff check src tests
	uv run --directory backend --no-sync ruff format --check src tests
	uv run --directory backend --no-sync mypy src/
	npm --prefix frontend run typecheck

format:
	uv run --directory backend --no-sync ruff format src tests

dev-backend:
	uv run --directory backend --no-sync uvicorn procureflow.main:app --reload --port 8000

dev-frontend:
	npm --prefix frontend run dev
