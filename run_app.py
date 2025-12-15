"""Convenience script that launches the backend and UI together."""

import subprocess
import os
import sys
import config
from logging_config import get_logger

logger = get_logger(__name__)

# Set paths to backend and frontend scripts
BACKEND_SCRIPT = os.path.join("api_main.py")              # adjust if your FastAPI app is named differently
FRONTEND_SCRIPT = os.path.join("ui/streamlit_app.py")    # adjust if yours is in a different folder

try:
    # Start FastAPI backend
    logger.info(f"Starting FastAPI backend on http://127.0.0.1:{config.PORT}...")
    backend = subprocess.Popen(
        [sys.executable, BACKEND_SCRIPT],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    logger.info(f"✅ FastAPI backend process started (PID: {backend.pid})")

    # Start Streamlit frontend
    logger.info(f"Starting Streamlit frontend on http://127.0.0.1:{config.FRONTEND_PORT}...")
    frontend = subprocess.Popen(
        ["streamlit", "run", FRONTEND_SCRIPT],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    logger.info(f"✅ Streamlit frontend process started (PID: {frontend.pid})")

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
