.PHONY: help install test lint format dev dev-backend dev-frontend clean

help:
	@echo "ProcureFlow OSS Development Commands:"
	@echo "  make install        Install both backend and frontend dependencies"
	@echo "  make test           Run backend test suite"
	@echo "  make lint           Run backend and frontend linters"
	@echo "  make format         Format code using ruff"
	@echo "  make dev-backend    Start backend FastAPI development server"
	@echo "  make dev-frontend   Start frontend Vite development server"
	@echo "  make clean          Clean cache directories and build artifacts"

install:
	cd backend && python -m uv venv && python -m uv pip install -e ".[dev]"
	cd frontend && npm install

test:
	cd backend && .venv/Scripts/pytest tests/ -v --cov=procureflow

lint:
	cd backend && .venv/Scripts/ruff check .
	cd backend && .venv/Scripts/mypy src/
	cd frontend && npm run typecheck

format:
	cd backend && .venv/Scripts/ruff format .

dev-backend:
	cd backend && .venv/Scripts/uvicorn procureflow.main:app --reload --port 8000

dev-frontend:
	cd frontend && npm run dev

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
