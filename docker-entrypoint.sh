#!/bin/sh
# NOTE: this file must keep LF line endings - see .gitattributes. A CRLF here
# makes the kernel read the shebang as "/bin/sh\r" and the container dies with
# "exec: no such file or directory", which points nowhere near the real cause.
set -e

: "${PORT:=8000}"
: "${API_HOST:=0.0.0.0}"
: "${LOG_LEVEL:=info}"

# Ensure the state directories exist on the mounted volumes. The image creates
# them, but a fresh named volume mounts over that and starts empty.
mkdir -p "$(dirname "${USER_DB_PATH:-/app/data/db/users.db}")"
mkdir -p "${VECTOR_DB_PATH:-/app/data/vector_index}"

echo "Starting Knowledge Manager API on ${API_HOST}:${PORT}"

exec uvicorn api.app:app \
    --host "${API_HOST}" \
    --port "${PORT}" \
    --log-level "$(echo "${LOG_LEVEL}" | tr '[:upper:]' '[:lower:]')" \
    --workers 1
