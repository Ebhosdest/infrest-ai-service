"""
Infrest AI Service — Main Application.

Run with: uvicorn app.main:app --host 0.0.0.0 --port 8090 --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import structlog

from app.config import get_settings
from app.routes.chat import router as chat_router
from app.routes.reports import router as reports_router

settings = get_settings()
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("starting_infrest_ai_service", port=settings.service_port)
    yield
    logger.info("shutting_down_infrest_ai_service")


app = FastAPI(
    title="Infrest AI Service",
    description=(
        "AI-powered Copilot and NLP Report Engine for Infrest ERP. "
        "Provides conversational assistance and natural language report generation."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register route groups
app.include_router(chat_router)
app.include_router(reports_router)


@app.get("/")
async def root():
    return {
        "service": "Infrest AI Service",
        "version": "1.0.0",
        "endpoints": {
            "copilot_chat": "/api/copilot/chat",
            "report_query": "/api/reports/query",
            "report_examples": "/api/reports/examples",
            "docs": "/docs",
        },
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}
