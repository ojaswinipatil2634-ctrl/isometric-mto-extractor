"""
FastAPI application entrypoint.

Wires together config, logging, error handlers, CORS, and routers.
Business logic never lives here - this file is only composition.
"""
import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import init_db
from app.core.errors import register_exception_handlers
from app.core.logging_config import configure_logging
from app.api.routes import health, extract, preprocess, ocr, detect, pipes, graph, business_rules, mto, verify

configure_logging()
logger = logging.getLogger(__name__)

settings = get_settings()

# Ensure runtime directories exist before the app starts serving requests.
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

# Create the SQLite schema (Phase 8) if it doesn't exist yet - safe to
# call on every startup, this is CREATE TABLE IF NOT EXISTS semantics.
init_db()

app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    description="Industrial isometric drawing MTO extraction API.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(health.router, prefix=settings.API_V1_PREFIX)
app.include_router(extract.router, prefix=settings.API_V1_PREFIX)
app.include_router(preprocess.router, prefix=settings.API_V1_PREFIX)
app.include_router(ocr.router, prefix=settings.API_V1_PREFIX)
app.include_router(detect.router, prefix=settings.API_V1_PREFIX)
app.include_router(pipes.router, prefix=settings.API_V1_PREFIX)
app.include_router(graph.router, prefix=settings.API_V1_PREFIX)
app.include_router(business_rules.router, prefix=settings.API_V1_PREFIX)
app.include_router(mto.router, prefix=settings.API_V1_PREFIX)
app.include_router(verify.router, prefix=settings.API_V1_PREFIX)
