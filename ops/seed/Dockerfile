# Customer 360 Aerospike seeder (one-shot)
FROM python:3.12-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY seed.py verify_c360.py ./

ENTRYPOINT ["uv", "run", "--no-sync", "python", "seed.py"]
CMD ["--host", "aerospike", "--port", "3000", "--customers", "100", "--country", "India"]
