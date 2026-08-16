"""Entry point to run the FastAPI application with Uvicorn."""

import uvicorn
from config import PORT, API_HOST, LOG_LEVEL

if __name__ == "__main__":
    uvicorn.run(
        "api.app:app",
        host=API_HOST,
        port=PORT,
        reload=False,
        log_level=LOG_LEVEL.lower(),
    )
