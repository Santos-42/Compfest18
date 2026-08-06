"""Compfest18 — Smart Logistics & Fraud Detection (Backend FastAPI).

Startup: init database (wilayah.sql) + load model XGBoost sekali, bukan per request.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router
from core.config import settings
from core.database import init_database
from services import fraud_service

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ===== STARTUP =====
    init_database()
    fraud_service.load_model()
    logger.info(" Backend siap. MOCK_MODE=%s", settings.USE_MOCK_MODE)
    yield
    # ===== SHUTDOWN =====
    logger.info("Server dimatikan.")


app = FastAPI(
    title="Compfest18 — Smart Logistics & Fraud Detection",
    version="3.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
def root():
    return {
        "app": "Compfest18",
        "docs": "/docs",
        "health": "/api/health",
    }
