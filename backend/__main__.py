"""Run the backend: python -m backend  (port from BACKEND_PORT, default 8010)."""

import uvicorn

from backend.app import config

if __name__ == "__main__":
    uvicorn.run("backend.app.main:app", host=config.BACKEND_HOST, port=config.BACKEND_PORT)
