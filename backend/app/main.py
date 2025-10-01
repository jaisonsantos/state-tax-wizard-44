import logging
import os
from pathlib import Path

from fastapi import FastAPI, Response
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from .routers import (
    analytics,
    audit,
    auth,
    billing,
    fees,
    reports,
    rules,
    store_settings,
    user,
)
from .db.database import engine
from .models import models
from .observability import setup_logging

# Configure logging once at startup
setup_logging()

if os.environ.get("APP_ENV", "dev") == "dev":
    # Create database tables (no-op if already present)
    models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Retail Delivery Fee Router API",
    description="SaaS for automated MN & CO delivery fee compliance",
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

# Serve documentation assets over the API domain so frontend links resolve.
DOCS_DIR = None
for parent in Path(__file__).resolve().parents:
    candidate = parent / "docs"
    if candidate.is_dir():
        DOCS_DIR = candidate
        break

if DOCS_DIR is not None:
    app.mount(
        "/api/files/docs",
        StaticFiles(directory=str(DOCS_DIR), html=False),
        name="docs_static",
    )
else:
    logging.getLogger(__name__).warning(
        "Documentation assets directory not found; skipping /api/files/docs mount."
    )

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://localhost:3000",
        "http://localhost",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type"],
)

# Health check
@app.get("/healthz")
async def health_check():
    return {"status": "healthy"}


@app.get("/docs", include_in_schema=False)
async def redirect_docs() -> RedirectResponse:
    """Preserve the legacy /docs URL by redirecting to /api/docs."""

    return RedirectResponse(url="/api/docs")

# Include routers
app.include_router(auth.router, prefix="/api")
app.include_router(user.router, prefix="/api")
app.include_router(fees.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(rules.router, prefix="/api")
app.include_router(billing.router, prefix="/api")
app.include_router(audit.router, prefix="/api")
app.include_router(store_settings.router, prefix="/api")


@app.get("/metrics")
async def metrics() -> Response:
    """Expose Prometheus metrics."""

    payload = generate_latest()
    return Response(content=payload, media_type=CONTENT_TYPE_LATEST)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
