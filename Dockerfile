# syntax=docker/dockerfile:1.4
# Stage 1: Builder
# Using linux/amd64 for compatibility across Mac (Intel/M-series) and Linux
FROM --platform=linux/amd64 python:3.10-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app
# Install build-essential only where it's needed
RUN apt-get update && apt-get install -y build-essential

COPY pyproject.toml uv.lock README.md ./
# Install dependencies into a specific folder
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --target /install .

# Stage 2: Final Runtime
FROM --platform=linux/amd64 python:3.10-slim
WORKDIR /app

# Copy the pre-installed packages from the builder
COPY --from=builder /install /usr/local/lib/python3.10/site-packages
COPY src ./src

EXPOSE 8000
CMD ["uvicorn", "dacke.app:app", "--host", "0.0.0.0", "--port", "8000"]