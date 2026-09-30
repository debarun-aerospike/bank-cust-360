# Customer 360 FastAPI API + load lab
# Build from repo root: docker compose build backend
#   context: .  dockerfile: backend/Dockerfile
FROM python:3.12-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    SEED_DIR=/app/ops/seed

COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY backend/app ./app
COPY ops/seed/seed.py ops/seed/verify_c360.py ./ops/seed/

EXPOSE 8000

CMD ["uv", "run", "--no-sync", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
