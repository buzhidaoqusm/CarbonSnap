# syntax=docker/dockerfile:1

# ---- builder: resolve dependencies from the lockfile -----------------------
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.10.4 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Dependency layer: only invalidated when the lockfile changes.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# ---- runtime ---------------------------------------------------------------
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

# /data is the mount point for the database, uploads and the FAISS index. It
# must exist and belong to the app user in the image: a fresh named volume
# copies this ownership, otherwise it is root-owned and startup cannot write.
RUN useradd --create-home --uid 10001 carbonsnap \
    && mkdir -p /data \
    && chown carbonsnap:carbonsnap /data

WORKDIR /app

COPY --from=builder --chown=carbonsnap:carbonsnap /app/.venv /app/.venv
COPY --chown=carbonsnap:carbonsnap . /app

USER carbonsnap

EXPOSE 5000

# run.py is the local dev entrypoint; the container serves through gunicorn.
# Migrate first: nothing else creates the schema in a fresh volume (run.py's
# create_all() never runs here). Once, before gunicorn forks its workers.
CMD ["sh", "-c", "flask --app 'app:create_app()' db upgrade && exec gunicorn -c gunicorn.conf.py -b 0.0.0.0:5000 'app:create_app()'"]
