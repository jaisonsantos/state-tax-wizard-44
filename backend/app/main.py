from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from .routers import auth, fees, reports, rules, billing, audit, user, store_settings
from .db.database import engine
from .models import models
from .observability import setup_logging

# Configure logging once at startup
setup_logging()

# Create database tables (no-op if already present)
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Retail Delivery Fee Router API",
    description="SaaS for automated MN & CO delivery fee compliance",
    version="1.0.0"
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

# Include routers
app.include_router(auth.router, prefix="/api")
app.include_router(user.router, prefix="/api")
app.include_router(fees.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
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