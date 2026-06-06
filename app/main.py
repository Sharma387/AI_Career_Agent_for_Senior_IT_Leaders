from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.rate_limit import RateLimitMiddleware
from app.core.scheduler.job_scheduler import job_scheduler
from app.db.models import init_db
from app.api.routes import router
from app.api.auth import router as auth_router

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    # Start the job scraping scheduler
    print("LIFESPAN: Starting job scheduler...")
    try:
        job_scheduler.start()
        print("LIFESPAN: Job scheduler started successfully")
    except Exception as e:
        print(f"LIFESPAN: Error starting job scheduler: {e}")
        import traceback
        traceback.print_exc()
    yield
    # Shutdown the scheduler when app stops
    print("LIFESPAN: Shutting down job scheduler...")
    try:
        job_scheduler.shutdown()
        print("LIFESPAN: Job scheduler shut down successfully")
    except Exception as e:
        print(f"LIFESPAN: Error shutting down job scheduler: {e}")
        import traceback
        traceback.print_exc()


app = FastAPI(
    title="AI Career Agent",
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RateLimitMiddleware, requests_per_minute=settings.RATE_LIMIT_PER_MINUTE)

app.include_router(auth_router)
app.include_router(router)


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}


@app.get("/")
async def root():
    return {
        "message": "Welcome to the AI Career Agent API",
        "docs": "/docs",
    }
