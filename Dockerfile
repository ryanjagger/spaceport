# Base images are pinned to a patch version and Debian release so every build matches.

FROM node:22.23.3-bookworm-slim AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12.15-slim-bookworm AS base
COPY --from=ghcr.io/astral-sh/uv:0.12.13 /uv /bin/uv
ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    SEED_FILE=/app/data/seed.json
WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev
COPY backend/schema.sql backend/entrypoint.sh ./
COPY backend/app ./app
COPY backend/scripts ./scripts

# docker compose --profile test run --rm test
FROM base AS test
RUN uv sync --frozen
COPY backend/tests ./tests
CMD ["pytest"]

# Last stage, so it is the default target (Railway builds this one).
FROM base AS runtime
COPY data/seed.json ./data/seed.json
COPY --from=frontend /frontend/dist ./static
CMD ["./entrypoint.sh"]
