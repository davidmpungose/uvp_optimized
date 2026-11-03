from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.services.api_settings import ApiSettings


def create_app() -> FastAPI:
    settings = ApiSettings.from_environment()
    application = FastAPI(
        title="Optimized UVP Multi-Quarter Reporting API",
        version="1.1.0",
        description=(
            "Read-only API supporting multiple selected quarters for "
            "case lists, summaries and trader history."
        ),
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.allowed_origins),
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["*"],
    )
    application.include_router(router)
    return application


app = create_app()
