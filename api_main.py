"""Entry point to run the FastAPI application with Uvicorn."""

import uvicorn
from config import PORT, API_HOST, LOG_LEVEL

host = API_HOST.replace("http://", "").replace("https://", "")

if __name__ == "__main__":
    uvicorn.run("api.app:app", host=host, port=PORT, reload=False, log_level=LOG_LEVEL.lower())
