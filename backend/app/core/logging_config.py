"""
Centralized logging configuration.

Every module should call `logging.getLogger(__name__)` and rely on the
setup done here, rather than configuring logging ad hoc.
"""
import logging
import sys

from app.core.config import get_settings


def configure_logging() -> None:
    settings = get_settings()

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(settings.LOG_LEVEL)

    # Avoid duplicate handlers on reload
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    # Quiet down noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
