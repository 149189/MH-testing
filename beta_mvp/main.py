from fastapi import FastAPI

from api.routes import health
from api.routes import verify
from api.routes import review
from api.routes import analytics
from db.session import Base, engine

app = FastAPI(title="Agentic Multilingual News Verification API", version="0.1.0")


@app.on_event("startup")
async def startup_event() -> None:
    # Ensure database tables exist
    Base.metadata.create_all(bind=engine)
    return None


@app.on_event("shutdown")
async def shutdown_event() -> None:
    # Place graceful shutdown logic here
    return None


app.include_router(health.router, prefix="/api")
app.include_router(verify.router, prefix="/api")
app.include_router(review.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
