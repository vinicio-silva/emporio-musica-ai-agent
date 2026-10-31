"""Application entrypoint for Empório da Música server.

Initializes database if missing, configures environment settings,
and runs Uvicorn ASGI server hosting the FastAPI backend and storefront.
"""

from __future__ import annotations

import os
from pathlib import Path
import uvicorn
from dotenv import load_dotenv

from src.database import DEFAULT_DB_PATH, init_db

load_dotenv()


def main() -> None:
    # Ensure SQLite database exists
    if not DEFAULT_DB_PATH.exists():
        print("Database not found. Ingesting CSV datasets into SQLite...")
        init_db()
        print("Database initialized successfully.")

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    debug = os.getenv("DEBUG", "false").lower() == "true"

    print(f"Starting Empório da Música server on http://{host}:{port}")
    print("Press CTRL+C to stop.")

    uvicorn.run(
        "src.api:app",
        host=host,
        port=port,
        reload=debug,
    )


if __name__ == "__main__":
    main()
