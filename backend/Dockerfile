FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off

# Install system dependencies (build tools, PostgreSQL client, OCR utilities)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Install uv for ultra-fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Copy project specifications, README, and source code for package installation
COPY pyproject.toml README.md ./
COPY src/ ./src/
RUN uv pip install --system --no-cache -e ".[dev]"

# Copy application migrations, scripts, and remaining files
COPY . /app

EXPOSE 8000

CMD ["uvicorn", "procureflow.main:app", "--host", "0.0.0.0", "--port", "8000"]
