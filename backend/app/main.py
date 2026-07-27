from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routers import chat, explain, health, metadata, monte_carlo, prediction, scenario, validation
from app.services.artifacts import load_artifact


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description="Credit risk scoring backend with SHAP explainability and LLM orchestration.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(metadata.router)
    app.include_router(validation.router)
    app.include_router(prediction.router)
    app.include_router(explain.router)
    app.include_router(scenario.router)
    app.include_router(monte_carlo.router)
    app.include_router(chat.router)

    frontend_dir = Path(__file__).resolve().parents[2] / "frontend"
    if frontend_dir.exists():
        app.mount("/dashboard/static", StaticFiles(directory=str(frontend_dir)), name="dashboard-static")

        @app.get("/", include_in_schema=False)
        def dashboard_root():
            return FileResponse(frontend_dir / "index.html")

        @app.get("/dashboard", include_in_schema=False)
        def dashboard_page():
            return FileResponse(frontend_dir / "index.html")

    @app.on_event("startup")
    def _startup() -> None:
        load_artifact()

    return app


app = create_app()

