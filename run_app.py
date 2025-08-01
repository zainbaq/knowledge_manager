"""Convenience script that launches the backend and UI together."""

import subprocess
import os
import sys

# Set paths to backend and frontend scripts
BACKEND_SCRIPT = os.path.join("api_main.py")              # adjust if your FastAPI app is named differently
FRONTEND_SCRIPT = os.path.join("ui/streamlit_app.py")    # adjust if yours is in a different folder

try:
    # Start FastAPI backend
    backend = subprocess.Popen(
        [sys.executable, BACKEND_SCRIPT],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    print("✅ FastAPI backend started on http://127.0.0.1:8000")

    # Start Streamlit frontend
    frontend = subprocess.Popen(
        ["streamlit", "run", FRONTEND_SCRIPT],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    print("✅ Streamlit frontend started on http://127.0.0.1:8501")

    # Wait for both processes
    backend.wait()
    frontend.wait()

except KeyboardInterrupt:
    print("\nShutting down...")

    backend.terminate()
    frontend.terminate()

    backend.wait()
    frontend.wait()
