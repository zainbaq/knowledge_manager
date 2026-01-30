"""Convenience script that launches the backend and UI together."""

import subprocess
import os
import sys
import config
from logging_config import get_logger

logger = get_logger(__name__)

# Set paths to backend and frontend
BACKEND_SCRIPT = os.path.join("api_main.py")
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "next")

try:
    # Start FastAPI backend
    logger.info(f"Starting FastAPI backend on http://127.0.0.1:{config.PORT}...")
    backend = subprocess.Popen(
        [sys.executable, BACKEND_SCRIPT],
    )
    logger.info(f"✅ FastAPI backend process started (PID: {backend.pid})")

    # Start Next.js frontend
    logger.info(f"Starting Next.js frontend on http://127.0.0.1:{config.FRONTEND_PORT}...")
    frontend = subprocess.Popen(
        ["npm", "run", "dev", "--", "-p", str(config.FRONTEND_PORT)],
        cwd=FRONTEND_DIR,
    )
    logger.info(f"✅ Next.js frontend process started (PID: {frontend.pid})")

    logger.info("Both processes running. Press Ctrl+C to stop.")

    # Wait for both processes
    backend.wait()
    frontend.wait()

except KeyboardInterrupt:
    logger.info("Received shutdown signal...")

    logger.info(f"Terminating backend process (PID: {backend.pid})...")
    backend.terminate()
    # frontend.terminate()

    backend.wait()
    # frontend.wait()

    logger.info("Shutdown complete")
