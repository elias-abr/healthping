# ─── Build stage ─────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build deps for any packages that compile extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --target /install .

# ─── Runtime stage ───────────────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

# Create a non-root user
RUN groupadd --system healthping && \
    useradd --system --gid healthping --home-dir /app --shell /usr/sbin/nologin healthping

# Copy installed packages from builder
COPY --from=builder /install /usr/local/lib/python3.12/site-packages

# Copy application source
COPY --chown=healthping:healthping src ./src

USER healthping

ENTRYPOINT ["python", "-m", "healthping.cli"]
CMD ["monitor", "--config", "/app/config.yaml"]
