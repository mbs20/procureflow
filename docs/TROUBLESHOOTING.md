# Troubleshooting Guide

This guide addresses common setup, Docker runtime, and operational issues when running ProcureFlow OSS.

---

## 1. Port Conflicts (5173, 8000, 5432, 6379)

### Symptom
`docker compose up` fails with:
```
Error response from daemon: Ports are not available: exposing port TCP 0.0.0.0:5173 -> 0.0.0.0:0: listen tcp 0.0.0.0:5173: bind: address already in use
```

### Solution
Another local service (e.g. Vite dev server, local PostgreSQL, or Redis) is bound to these ports.
- Identify the process on Windows:
  ```powershell
  Get-NetTCPConnection -LocalPort 5173, 8000, 5432, 6379 | Select-Object LocalPort, OwningProcess
  ```
- Identify the process on Linux/macOS:
  ```bash
  lsof -i :5173 -i :8000 -i :5432 -i :6379
  ```
- Or override ports in your `.env`:
  ```env
  PORT=8080
  DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5433/procureflow
  ```

---

## 2. Docker Daemon Not Running

### Symptom
```
Cannot connect to the Docker daemon at unix:///var/run/docker.sock. Is the docker daemon running?
```

### Solution
Ensure Docker Desktop or the Docker service is running:
- **Windows**: Open Docker Desktop from the Start Menu. Wait for the engine icon to turn solid green.
- **Linux**: Run `sudo systemctl start docker`.

---

## 3. Database Migration / Connection Refusal

### Symptom
Backend container logs show:
```
sqlalchemy.exc.OperationalError: (psycopg2.OperationalError) connection to server at "postgres" (172.x.x.x), port 5432 failed: Connection refused
```

### Solution
1. Verify PostgreSQL container health:
   ```bash
   docker compose ps postgres
   ```
2. Check database container logs:
   ```bash
   docker compose logs postgres
   ```
3. Ensure Compose healthchecks have completed before running migrations:
   The backend service uses `depends_on: postgres: condition: service_healthy` to guarantee PostgreSQL is accepting connections prior to running Alembic.
4. If migrating manually:
   ```bash
   docker compose exec backend alembic upgrade head
   ```

---

## 4. Resetting Demo Data

### Symptom
You want a fresh set of demo RFQs and supplier quotes without affecting any custom-created RFQs.

### Solution
Run the demo seeder with the `--reset` flag:
```bash
docker compose run --rm seed-demo python -m procureflow.scripts.seed_demo --reset
```
This safely deletes only records prefixed with `[DEMO]` (and their associated quotations, scores, and decision contexts) and re-populates the pristine demonstration dataset.

---

## 5. Production Startup Configuration Rejection

### Symptom
Backend exits immediately on startup with:
```
ValueError: Insecure production configuration: SECRET_KEY is set to default development secret.
```

### Solution
In production (`ENVIRONMENT=production`), ProcureFlow enforces strict security invariants. You must supply:
1. A strong `SECRET_KEY` (at least 32 characters):
   ```bash
   openssl rand -hex 32
   ```
2. A non-default `API_KEY`.
3. Explicit `CORS_ORIGINS` (wildcard `*` is strictly disallowed in production).
4. A real LLM provider (`OPENAI_API_KEY` or `ANTHROPIC_API_KEY`) if `PROCUREFLOW_LLM_PROVIDER` is not set to an authorized production provider.
5. `DEBUG=False`.

---

## 6. Celery Worker Missing Redis Connection

### Symptom
Quotation document extraction remains stuck in `PENDING` or worker container logs:
```
Error 111 connecting to redis:6379. Connection refused.
```

### Solution
1. Ensure the Redis container is healthy:
   ```bash
   docker compose ps redis
   ```
2. Restart the worker service:
   ```bash
   docker compose restart worker
   ```
