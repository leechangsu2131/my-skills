from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from webapp.store import WorkspaceStore


APP_DIR = Path(__file__).parent
TEMPLATES = Jinja2Templates(directory=str(APP_DIR / "templates"))


def create_app(workspace: str | Path | None = None) -> FastAPI:
    root = Path(workspace or Path.cwd())
    store = WorkspaceStore(root)
    app = FastAPI(title="Classmanage Exam Grader")
    app.state.store = store
    app.mount("/static", StaticFiles(directory=str(APP_DIR / "static")), name="static")

    @app.get("/")
    async def index(request: Request):
        return TEMPLATES.TemplateResponse(
            request,
            "index.html",
            {"request": request, "batches": []},
        )

    return app


app = create_app()
