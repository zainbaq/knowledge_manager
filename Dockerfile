# Build stage
FROM python:3.11-slim AS builder

WORKDIR /app

# Build dependencies for packages without prebuilt wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --timeout 120 -r requirements.txt

# Production stage
FROM python:3.11-slim AS production

WORKDIR /app

# Runtime dependencies only.
# libmagic1 backs python-magic's MIME sniffing. Without it the import fails and
# validate_upload_files() silently degrades to extension-only checks - uploads
# are accepted on filename alone. Not optional in a real deployment.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Create non-root user
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

COPY --chown=appuser:appgroup . .

# Persistent state lives on mounted volumes, never in the image layer.
# VECTOR_DB_PATH and USER_DB_PATH default to paths inside the project directory,
# which is the classic lift-and-shift data-loss trap - they are pointed at these
# directories in docker-compose.yml.
RUN mkdir -p /app/data/vector_index /app/data/db && \
    chown -R appuser:appgroup /app/data

RUN chmod +x docker-entrypoint.sh

USER appuser

EXPOSE 8000

ENTRYPOINT ["./docker-entrypoint.sh"]
