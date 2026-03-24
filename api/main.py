import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db import check_db_connection
from api.scheduler import start_scheduler, stop_scheduler
from api.routers import recommend, session, library

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🎵 VibeFlow API starting...")
    if check_db_connection():
        logger.info("Database connected")
    else:
        logger.error("Database connection failed")
    start_scheduler()
    yield
    stop_scheduler()
    logger.info("VibeFlow API shutdown")


app = FastAPI(
    title="VibeFlow API",
    description="Intelligent music recommendation engine",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(recommend.router, prefix="/recommend", tags=["Recommendations"])
app.include_router(session.router,   prefix="/session",   tags=["Session"])
app.include_router(library.router,   prefix="/library",   tags=["Library"])


@app.get("/health")
def health():
    return {"status": "ok", "db": check_db_connection()}
