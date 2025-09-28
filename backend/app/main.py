from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import auth, fees, reports, rules, billing, audit, user
from .db.database import engine
from .models import models

# Create database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Retail Delivery Fee Router API",
    description="SaaS for automated MN & CO delivery fee compliance",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://localhost:3000", "http://localhost"],
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)