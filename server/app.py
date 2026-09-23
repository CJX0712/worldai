# Author: 晨星
"""App factory: assembly only, zero business logic (DIP container)."""
from __future__ import annotations

import sys
from pathlib import Path

# Allow `uvicorn server.app:app` from the repo root without packaging.
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.agent import Agent
from core.pipeline import build_pipeline

from . import routes


def create_app() -> FastAPI:
    pipeline = build_pipeline()
    routes.bind(pipeline, Agent(pipeline, pipeline._llm))

    app = FastAPI(title="WorldAI", version="0.1.0", docs_url="/api/docs")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # MVP local-first; tighten before public deploy
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(routes.router)
    return app


app = create_app()


def main() -> None:
    import os

    import uvicorn

    port = int(os.environ.get("WORLDAI_PORT", "8765"))
    uvicorn.run("server.app:app", host="127.0.0.1", port=port, reload=False)


if __name__ == "__main__":
    main()
