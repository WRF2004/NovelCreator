from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.books import router as books_router
from app.api.generation import router as generation_router
from app.api.training import router as training_router
from app.core.config import ensure_storage_dirs, settings
from app.db.database import Base, engine
from app.db.migrations import run_migrations


def create_app() -> FastAPI:
    ensure_storage_dirs()
    Base.metadata.create_all(bind=engine)
    run_migrations()

    app = FastAPI(title=settings.app_name)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(training_router, prefix=settings.api_prefix)
    app.include_router(books_router, prefix=settings.api_prefix)
    app.include_router(generation_router, prefix=settings.api_prefix)

    @app.get("/")
    def root():
        return {"app": settings.app_name, "status": "ok"}

    @app.get("/health")
    def health():
        return {"ok": True}

    return app


app = create_app()
