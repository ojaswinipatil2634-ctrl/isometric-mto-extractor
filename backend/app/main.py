"""FastAPI application entrypoint."""
from __future__ import annotations

import logging

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.mock_mode:
        logger.warning(
            "GEMINI_API_KEY not set — starting in MOCK MODE. "
            "Set GEMINI_API_KEY in .env to enable live extraction."
        )
    else:
        logger.info("Starting with live Gemini Vision extraction (model=%s)", settings.model_name)
    yield


app = FastAPI(
    title=settings.app_name,
    description="Extracts a Material Take-Off (MTO) from a piping isometric drawing using Gemini Vision.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")
